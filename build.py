#!/usr/bin/env python3
"""build.py — generator planu obiadów (zero backendu).

Wejście  : plans/<id>/plan.yaml  +  recipes/*.md (frontmatter YAML)  +  ingredients.md (słownik)
Wyjście  : plans/<id>/demand.json  +  plans/<id>/index.html  +  plans/<id>/journal.json (seed)
           +  index.html (przekierowanie na najnowszy plan)

Zasady (rejestr [DECISION] w README):
  - demand[] = czysta agregacja składników z kart w meals[]; spiżarnia bazowa poza demandem;
    szt zaokrąglane w górę, kg/l do 2 miejsc. Komponenty NIE są rozwijane (gdy trzeba je kupić,
    planer wpisuje je jako osobny meal — jak sos/ciecierzyca w W31).
  - Walidacja: każda nazwa składnika w kartach i w planie musi być kanoniczna (lub aliasem)
    ze słownika, a jej jednostka — przeliczalna. Błąd = niezerowy kod wyjścia (gate dla CI).

Użycie:
  python3 build.py                 # zbuduj wszystkie plany w plans/
  python3 build.py 2026-W31        # zbuduj jeden plan
  python3 build.py --check         # tylko walidacja, bez zapisu (dla CI)
"""
from __future__ import annotations
import sys, re, json, math, html, unicodedata, datetime
from pathlib import Path
import yaml

WEEKDAY_DOW = ["Pn", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"]  # date.weekday(): Pn=0

ROOT = Path(__file__).resolve().parent
RECIPES_DIR = ROOT / "recipes"
PLANS_DIR = ROOT / "plans"
DICT_FILE = ROOT / "ingredients.md"

FRACTIONS = {0.25: "¼", 0.5: "½", 0.75: "¾", 0.33: "⅓", 0.34: "⅓", 0.66: "⅔", 0.67: "⅔"}


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Słownik składników (ingredients.md)
# --------------------------------------------------------------------------- #
class Dictionary:
    def __init__(self):
        self.by_name: dict[str, dict] = {}      # nazwa kanoniczna → {unit, category, pantry}
        self.alias: dict[str, str] = {}         # alias → nazwa kanoniczna
        self.categories: list[str] = []         # kolejność kategorii (poza spiżarnią)
        self.base: dict[str, float] = {}        # jednostka źródłowa → mnożnik do bazowej
        self.per_ingredient: dict[str, dict] = {}
        self.pack_label: dict[str, str] = {}

    def canonical(self, name: str) -> str | None:
        if name in self.by_name:
            return name
        return self.alias.get(name)


def load_dictionary() -> Dictionary:
    d = Dictionary()
    text = DICT_FILE.read_text(encoding="utf-8")

    # blok maszynowy (```yaml ... ```)
    m = re.search(r"```yaml\s*\n(.*?)```", text, re.S)
    if not m:
        raise BuildError("ingredients.md: brak bloku maszynowego ```yaml``` z konwersjami")
    machine = yaml.safe_load(m.group(1)) or {}
    units = machine.get("units", {})
    d.base = units.get("base", {})
    d.per_ingredient = units.get("per_ingredient", {})
    d.pack_label = machine.get("pack_label", {})

    # tabele składników per sekcja (## Nagłówek)
    section = None
    pantry = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            pantry = "spiżarnia" in section.lower()
            continue
        if not line.startswith("|") or section is None:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 2 or cols[0] in ("Nazwa kanoniczna", "") or set(cols[0]) <= {"-", ":"}:
            continue
        name, unit = cols[0], cols[1]
        aliases = cols[2] if len(cols) > 2 else ""
        if section != "Konwersje jednostek (blok maszynowy)":
            d.by_name[name] = {"unit": unit, "category": section, "pantry": pantry}
            for al in re.split(r"[,;]", aliases):
                al = al.strip()
                if al:
                    d.alias[al] = name
            if not pantry and section not in d.categories:
                d.categories.append(section)
    return d


# --------------------------------------------------------------------------- #
# Karty przepisów (recipes/*.md)
# --------------------------------------------------------------------------- #
def load_recipe(recipe_id: str) -> dict:
    path = RECIPES_DIR / f"{recipe_id}.md"
    if not path.exists():
        raise BuildError(f"brak karty przepisu: recipes/{recipe_id}.md")
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        raise BuildError(f"recipes/{recipe_id}.md: brak frontmatteru YAML")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    meta["_id"] = recipe_id
    meta["_subtitle"] = _subtitle(body)
    meta["_steps"] = _prep_steps(body)
    return meta


def _strip_md_links(s: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)


def _subtitle(body: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        line = _strip_md_links(line)
        line = re.sub(r"^Dodatki:\s*", "", line)
        return line if len(line) <= 90 else ""
    return ""


def _prep_steps(body: str) -> list[str]:
    steps, capture = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            capture = "przygotowanie" in line.lower()
            continue
        if capture:
            m = re.match(r"^\d+\.\s+(.*)$", line.strip())
            if m:
                steps.append(_strip_md_links(m.group(1)))
    return steps


# --------------------------------------------------------------------------- #
# Plan (plans/<id>/plan.yaml)
# --------------------------------------------------------------------------- #
def load_plan(plan_id: str) -> dict:
    path = PLANS_DIR / plan_id / "plan.yaml"
    if not path.exists():
        raise BuildError(f"brak planu: plans/{plan_id}/plan.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def meal_id(m) -> str:
    """Wpis w meals[] to id karty (str) albo mapa {id, servings}."""
    return m["id"] if isinstance(m, dict) else m


def meal_servings(m, default: float) -> float:
    """Porcje dla pojedynczego dania — override na dzień/danie albo domyślne planu.
    Pozwala zrobić jedno danie mniejsze (np. dzieci jedzą mniej / mniej mięsa),
    nie ruszając reszty planu."""
    return m["servings"] if isinstance(m, dict) and "servings" in m else default


# --------------------------------------------------------------------------- #
# Profil mięsa: przedział dania + klasyfikacja opakowania (migracja 02)
# --------------------------------------------------------------------------- #
PREFS_FILE = ROOT / "preferences.md"

# wektory testowe — bramka poprawności algorytmu ORAZ kalibracji profilu (adult 170 → 272–396).
# Brzegi 270/275/280 dyskryminują profil: przy adult 180 (lo=288) wektor 275→OK by padł.
MEAT_TEST_VECTORS = [(200, "ZA MAŁO", None), (270, "ZA MAŁO", None),
                     (275, "OK", 1), (280, "OK", 1), (300, "OK", 1), (396, "OK", 1),
                     (400, "ZA DUŻO", None), (450, "ZA DUŻO", None),
                     (600, "OK", 2), (700, "OK", 2)]


def load_meat_profile() -> dict:
    text = PREFS_FILE.read_text(encoding="utf-8")
    for m in re.finditer(r"```yaml\s*\n(.*?)```", text, re.S):
        data = yaml.safe_load(m.group(1)) or {}
        if "meat_profile" in data:
            return data["meat_profile"]
    raise BuildError("preferences.md: brak bloku `meat_profile`")


def meat_range(profile: dict) -> tuple[int, int]:
    """Przedział g mięsa/danie ze składu jedzących: adult × (adults + Σ mnożniki)."""
    a_lo, a_hi = profile["adult_g"]
    adults = profile.get("adults", 1)
    kids = profile.get("children", {}) or {}
    smin = sum(v[0] for v in kids.values())
    smax = sum(v[1] for v in kids.values())
    return round(a_lo * (adults + smin)), round(a_hi * (adults + smax))


def classify_package(w: float, lo: int, hi: int) -> tuple[str, int]:
    """W [g] → („OK", n) gdy istnieje największe n≥1 z W/n w [lo,hi];
    („ZA MAŁO", 0) gdy W<lo; („ZA DUŻO", 1) gdy W>hi bez podziału."""
    n = int(w // lo) if lo > 0 else 0
    while n >= 1:
        if lo <= w / n <= hi:
            return ("OK", n)
        n -= 1
    return ("ZA MAŁO", 0) if w < lo else ("ZA DUŻO", 1)


def selftest_classification(lo: int, hi: int, errors: list) -> None:
    # Wektory skalibrowane dla profilu 272–396 (adult 170). Uruchamiane ZAWSZE wobec
    # wyliczonego przedziału — dryf profilu (np. adult 180) wywali bramkę i wymusi
    # aktualizację wektorów. Przedział pozostaje wyliczany z preferences (bez stałej w logice).
    for w, status, n in MEAT_TEST_VECTORS:
        got = classify_package(w, lo, hi)
        if got[0] != status or (n is not None and got[1] != n):
            errors.append(f"klasyfikacja/kalibracja (przedział {lo}–{hi}): W={w} → {got}, "
                          f"oczekiwano „{status}”" + (f"/{n} dań" if n else "")
                          + " — dostosuj profil lub wektory")


# --------------------------------------------------------------------------- #
# Konwersja jednostek + agregacja demand
# --------------------------------------------------------------------------- #
def to_base(d: Dictionary, name: str, qty: float, unit: str, errors: list) -> tuple[str, float] | None:
    base_unit = d.by_name[name]["unit"]
    per = d.per_ingredient.get(name, {})
    if unit in per:
        return base_unit, qty * per[unit]
    if unit in d.base:
        return base_unit, qty * d.base[unit]
    errors.append(f"składnik „{name}”: brak przelicznika jednostki „{unit}” "
                  f"(dodaj do units.per_ingredient w ingredients.md)")
    return None


def round_demand(base_unit: str, qty: float) -> float:
    if base_unit == "szt":
        return math.ceil(round(qty, 6))
    return round(qty, 2)


def validate_plan(plan: dict, recipes: dict, errors: list) -> None:
    """Spójność planu: kalendarz + przepływ komponentów (produkcja/konsumpcja).

    Łapie m.in. „makaron w dodatkowy dzień, a sos zaplanowany raz i się nie wyrabia"
    — czyli danie-konsument (`components: [<składnik-bazowy>]`) bez pokrycia w bazie.
    """
    frm, to = str(plan["period"]["from"]), str(plan["period"]["to"])
    producers: dict[str, list] = {}       # component_id → [(date, factor)]
    consumers: list = []                  # (date, factor, component_id, consumer_id)

    for day in plan["days"]:
        date = str(day["date"])
        try:
            wd = datetime.date.fromisoformat(date).weekday()
            if day.get("dow") and day["dow"] != WEEKDAY_DOW[wd]:
                errors.append(f"{date}: etykieta dnia „{day['dow']}” ≠ kalendarz "
                              f"„{WEEKDAY_DOW[wd]}”")
        except ValueError:
            errors.append(f"{date}: niepoprawna data w plan.yaml")
            continue
        if not (frm <= date <= to):
            errors.append(f"{date}: poza okresem planu {frm}–{to}")
        for m in day.get("meals", []):
            rid = meal_id(m)
            r = recipes.get(rid)
            if r is None:
                continue
            factor = meal_servings(m, plan["servings"]) / r.get("base_servings", 2)
            producers.setdefault(rid, []).append((date, factor))
            for c in r.get("components", []):
                cc = recipes.get(c)
                if cc is None:
                    errors.append(f"{rid}: komponent „{c}” — brak karty recipes/{c}.md")
                elif cc.get("type") == "składnik-bazowy":
                    consumers.append((date, factor, c, rid))

    for cdate, _cf, comp, consumer_id in consumers:
        prods = producers.get(comp)
        if not prods:
            errors.append(f"{consumer_id} ({cdate}) potrzebuje bazy „{comp}”, której nie ma "
                          f"w planie — dodaj ją jako danie albo usuń zależność (inaczej „sam "
                          f"makaron bez sosu”)")
        elif min(pd for pd, _ in prods) > cdate:
            errors.append(f"{consumer_id} ({cdate}): baza „{comp}” gotowana dopiero "
                          f"{min(pd for pd, _ in prods)} — konsumpcja przed produkcją")

    for comp in {c for _, _, c, _ in consumers}:
        capacity = sum(recipes[comp].get("serves", 1) * pf for _, pf in producers.get(comp, []))
        needed = sum(cf for _, cf, c, _ in consumers if c == comp)
        if needed > capacity + 1e-9:
            errors.append(f"baza „{comp}”: batch(e) starczą na {num(capacity)} dań, a plan ma "
                          f"{num(needed)} dań-konsumentów — zwiększ `servings` bazy lub jej "
                          f"`serves`, albo usuń danie (inaczej część dni = sam dodatek bez bazy)")


def build_demand(plan: dict, recipes: dict, d: Dictionary, mrange: tuple, errors: list):
    """Zwraca (meals[], demand[]). Składniki na wagę/szt sumuje po jednostce bazowej;
    mięso w `unit: danie` liczy przedziałem (mrange g/danie), pomija spiżarnię."""
    lo, hi = mrange
    meals_out = []
    totals: dict[str, float] = {}
    meat_dania: dict[str, float] = {}
    for day in plan["days"]:
        for m in day.get("meals", []):
            rid = meal_id(m)
            r = recipes[rid]
            servings = meal_servings(m, plan["servings"])
            scale = servings / r.get("base_servings", 2)
            meals_out.append({"date": str(day["date"]), "recipe_id": rid,
                              "servings": servings})
            for ing in r.get("ingredients", []):
                canon = d.canonical(ing["name"])
                if canon is None:
                    errors.append(f"recipes/{rid}.md: nieznany składnik „{ing['name']}” "
                                  f"(dodaj do ingredients.md)")
                    continue
                if d.by_name[canon]["pantry"]:
                    continue  # spiżarnia bazowa poza demandem
                if ing["unit"] == "danie":            # mięso przedziałowe
                    meat_dania[canon] = meat_dania.get(canon, 0.0) + ing["qty"] * scale
                    continue
                conv = to_base(d, canon, ing["qty"] * scale, ing["unit"], errors)
                if conv is None:
                    continue
                _, base_qty = conv
                totals[canon] = totals.get(canon, 0.0) + base_qty

    demand_out = []
    for name, meta in d.by_name.items():  # kolejność ze słownika → stabilny diff
        if name in meat_dania:
            dn = meat_dania[name]
            demand_out.append({"ingredient": name, "unit": "kg",
                               "qty": round(dn * (lo + hi) / 2 / 1000, 2),
                               "qty_range": [round(dn * lo / 1000, 2), round(dn * hi / 1000, 2)],
                               "dania": round(dn, 2)})
        elif name in totals:
            demand_out.append({"ingredient": name, "unit": meta["unit"],
                               "qty": round_demand(meta["unit"], totals[name])})
    return meals_out, demand_out


# --------------------------------------------------------------------------- #
# journal.json (seed) — jeden wpis na dzień z daniem głównym; nie nadpisuje wyników
# --------------------------------------------------------------------------- #
def build_journal(plan: dict, recipes: dict, existing: dict | None) -> dict:
    prev = {e["date"]: e for e in (existing or {}).get("entries", [])}
    entries = []
    for day in plan["days"]:
        obiady = [meal_id(m) for m in day.get("meals", [])
                  if recipes[meal_id(m)].get("type") == "obiad"]
        if not obiady:
            continue
        date = str(day["date"])
        if date in prev:
            entries.append(prev[date])
        else:
            entries.append({"date": date, "planned": obiady[0], "actual": None,
                            "outcome": "pending"})
    return {"plan_id": plan["plan_id"], "baseline_revision": plan["revision"], "entries": entries}


# --------------------------------------------------------------------------- #
# Formatowanie ilości
# --------------------------------------------------------------------------- #
def num(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def frac(x: float) -> str:
    whole = int(x)
    rest = round(x - whole, 2)
    if rest in FRACTIONS:
        return (str(whole) if whole else "") + FRACTIONS[rest]
    return num(x)


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def pl_dania(n: float) -> str:
    """Polska odmiana: 1 danie, 2–4 dania, 5+ dań (dla całkowitych)."""
    s = num(n)
    if n == 1:
        return f"{s} danie"
    if float(n).is_integer() and 2 <= int(n) % 10 <= 4 and not 12 <= int(n) % 100 <= 14:
        return f"{s} dania"
    return f"{s} dań"


def fmt_shop(name: str, qty: float, base_unit: str, d: Dictionary) -> str:
    if base_unit == "kg":
        return f"{num(qty)} kg" if qty >= 1 else f"{num(qty * 1000)} g"
    if base_unit == "l":
        return f"{num(qty)} l" if qty >= 1 else f"{num(qty * 1000)} ml"
    label = d.pack_label.get(name)
    n = int(qty)
    if label:
        return f"{n} {label}"
    return f"{n} szt."


def fmt_ing(ing: dict, scale: float = 1.0, mrange: tuple | None = None) -> str:
    if ing.get("unit") == "danie":               # mięso przedziałowe
        q = frac(float(ing["qty"]) * scale)
        rng = f" · ~{mrange[0]}–{mrange[1]} g" if mrange else ""
        return f"{q} danie{rng}"
    q = frac(float(ing["qty"]) * scale)
    unit = ing.get("unit", "")
    unit = "" if unit == "szt" and q in ("½", "¼", "⅓", "¾", "⅔") else unit
    return f"{q} {unit}".strip() if unit else f"{q} szt."


# --------------------------------------------------------------------------- #
# Render HTML
# --------------------------------------------------------------------------- #
CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F5F0E8;color:#2A2520;padding:1rem;max-width:620px;margin:0 auto;font-size:15px;line-height:1.65}
header{padding:1rem 0 .5rem}
h1{font-size:21px;font-weight:600}
.meta{font-size:13px;color:#7A7268;margin-top:3px}
.wknav{display:flex;justify-content:space-between;gap:10px;margin-top:.7rem}
.wk-a,.wk-x{font-size:12px;font-weight:600;padding:5px 11px;border-radius:8px;border:1px solid #E4DDD4;text-decoration:none}
.wk-a{background:#FFF;color:#1D9E75}
.wk-a:active{background:#EDF8F2}
.wk-x{background:transparent;color:#C0B8AE;border-color:#EFE9E1}
h2{font-size:13px;font-weight:600;color:#1E1A17;margin:1.4rem 0 .55rem;padding-bottom:.3rem;border-bottom:1.5px solid #DDD6CC;text-transform:uppercase;letter-spacing:.05em}
.card{background:#FFF;border-radius:14px;border:1px solid #E4DDD4;padding:.75rem 1.2rem;margin-bottom:.75rem}
details.shop-cat{border-bottom:1px solid #F0EAE2}
details.shop-cat:last-child{border-bottom:none}
details.shop-cat>summary{list-style:none;padding:.65rem 0;font-size:14px;font-weight:600;color:#2A2520;cursor:pointer;display:flex;align-items:center;justify-content:space-between;-webkit-tap-highlight-color:transparent;user-select:none}
details.shop-cat>summary::-webkit-details-marker{display:none}
details.shop-cat>summary .ct{font-size:12px;color:#B0A89E;font-weight:400;margin-right:6px}
details.shop-cat>summary .arr{font-size:12px;color:#9A9088;display:inline-block;transition:transform .15s}
details.shop-cat[open]>summary .arr{transform:rotate(90deg)}
.shop-body{padding-bottom:.6rem}
.srow{display:flex;align-items:center;gap:10px;padding:5px 0;cursor:pointer;-webkit-tap-highlight-color:transparent}
.srow input[type=checkbox]{width:17px;height:17px;accent-color:#1D9E75;flex-shrink:0;cursor:pointer}
.srow label{flex:1;font-size:14px;cursor:pointer;transition:color .1s}
.srow .qty{color:#9A9088;font-size:13px;white-space:nowrap}
.srow.done label{text-decoration:line-through;color:#C0B8AE}
.plan{display:flex;flex-direction:column;gap:9px}
.prow{display:flex;gap:11px;align-items:flex-start}
.pday{font-size:12px;font-weight:600;color:#9A9088;width:80px;flex-shrink:0;padding-top:1px}
.pdot{width:9px;height:9px;border-radius:50%;background:#1D9E75;flex-shrink:0;margin-top:4px}
.pdot.rest{background:#DDD6CC}
.pinfo{flex:1}
.pdish{font-size:14px;font-weight:500;color:#1E1A17;line-height:1.35}
.pside{font-size:13px;color:#7A7268}
.ptag{display:inline-block;font-size:11px;background:#FDF4E2;border:1px solid #E8C97A;color:#6F4A00;border-radius:5px;padding:1px 6px;margin-left:5px;font-weight:500;vertical-align:middle}
.prest{font-size:14px;color:#B0A89E;font-style:italic}
.recipe{background:#FFF;border-radius:14px;border:1px solid #E4DDD4;margin-bottom:1rem;overflow:hidden}
.rhdr{padding:.9rem 1.2rem;border-bottom:1px solid #F0EAE2;display:flex;gap:12px;align-items:center}
.dbadge{flex-shrink:0;text-align:center;width:52px}
.dname{font-size:10px;font-weight:600;color:#9A9088;text-transform:uppercase;letter-spacing:.06em}
.dcircle{width:36px;height:36px;border-radius:50%;background:#1D9E75;color:#FFF;font-size:15px;font-weight:700;display:flex;align-items:center;justify-content:center;margin:2px auto 0}
.dcircle.sub{background:#B7A98E;font-size:18px}
.rtitle{font-size:16px;font-weight:600;color:#1E1A17;line-height:1.3}
.rside{font-size:13px;color:#7A7268;margin-top:2px}
.rbody{padding:.9rem 1.2rem}
.slbl{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:#9A9088;margin-bottom:.45rem}
.ings{list-style:none;margin-bottom:.2rem}
.ing{display:flex;justify-content:space-between;align-items:baseline;padding:4px 0;border-bottom:1px solid #F5EFE8;font-size:14px}
.ing:last-child{border-bottom:none}
.iq{color:#9A9088;font-size:13px;margin-left:10px;white-space:nowrap;flex-shrink:0}
details.sacc{border:1px solid #D8EEE2;border-radius:10px;margin-top:.8rem;overflow:hidden}
details.sacc>summary{list-style:none;background:#EDF8F2;padding:.55rem .9rem;font-size:13.5px;font-weight:600;color:#0F6E56;cursor:pointer;display:flex;align-items:center;justify-content:space-between;-webkit-tap-highlight-color:transparent;user-select:none}
details.sacc>summary::-webkit-details-marker{display:none}
details.sacc>summary .sc{font-size:12px;color:#7A9E8F;font-weight:400}
details.sacc>summary .arr{font-size:11px;display:inline-block;transition:transform .15s}
details.sacc[open]>summary .arr{transform:rotate(90deg)}
.sbody{padding:.7rem .9rem;border-top:1px solid #D8EEE2}
.slist{list-style:none;counter-reset:s 0}
.slist li{counter-increment:s 1;padding:5px 0 5px 30px;position:relative;font-size:14px;border-bottom:1px solid #F5EFE8;line-height:1.5}
.slist li:last-child{border-bottom:none}
.slist li::before{content:counter(s);position:absolute;left:0;top:6px;width:21px;height:21px;border-radius:50%;background:#F0EAE2;color:#9A9088;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600}
.note{border-radius:0 8px 8px 0;padding:.5rem .8rem;font-size:13px;line-height:1.5;margin-top:.7rem}
.nwarn{background:#FDF4E2;border-left:3px solid #D4922B;color:#6F4A00}
.note strong{font-weight:600}
footer{text-align:center;font-size:12px;color:#C0B8AE;padding:1.5rem 0 2rem}
@media print{body{background:#FFF;padding:0}details{display:block}details>summary{display:none}details>.sbody,details>.shop-body{display:block!important}.recipe,.card{break-inside:avoid;border:1px solid #CCC}}"""

PL_DATE = None  # dd.mm z ISO


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def dm(date: str) -> str:
    y, m, d = str(date).split("-")
    return f"{d}.{m}"


def render_html(plan: dict, recipes: dict, demand: list, d: Dictionary,
                neighbors: tuple = (None, None), mrange: tuple = (0, 0)) -> str:
    prev_id, next_id = neighbors
    P = []
    frm, to = plan["period"]["from"], plan["period"]["to"]
    P.append('<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8">')
    P.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    P.append(f'<title>{esc(plan["title"])} — {esc(plan["plan_id"])}</title>')
    P.append(f"<style>\n{CSS}\n</style></head><body>")
    P.append("<header>")
    P.append(f'<h1>{esc(plan["title"])}</h1>')
    P.append(f'<p class="meta">Tydzień {esc(plan["plan_id"])} · {dm(frm)}–{dm(to)} · '
             f'{num(plan["servings"])} porcje</p>')
    # ---- Nawigacja tydzień ← → (linki względne do sąsiednich planów) ----
    left = (f'<a class="wk-a" href="../{esc(prev_id)}/">‹ {esc(prev_id)}</a>'
            if prev_id else '<span class="wk-x">‹ poprzedni</span>')
    right = (f'<a class="wk-a" href="../{esc(next_id)}/">{esc(next_id)} ›</a>'
             if next_id else '<span class="wk-x">następny ›</span>')
    P.append(f'<nav class="wknav">{left}{right}</nav>')
    P.append("</header>")

    # ---- Lista zakupów (grupy = kategorie słownika) ----
    P.append("<h2>Lista zakupów</h2>")
    P.append('<div class="card" style="padding:.4rem 1.2rem">')
    by_cat: dict[str, list] = {}
    for item in demand:
        cat = d.by_name[item["ingredient"]]["category"]
        by_cat.setdefault(cat, []).append(item)
    for cat in d.categories:
        items = by_cat.get(cat)
        if not items:
            continue
        P.append('<details class="shop-cat"><summary>' + esc(cat) +
                  f' <span class="ct">{len(items)} poz.</span><span class="arr">▸</span></summary>')
        P.append('<div class="shop-body">')
        for it in items:
            if "qty_range" in it:                 # mięso przedziałowe
                gmin, gmax = round(it["qty_range"][0] * 1000), round(it["qty_range"][1] * 1000)
                q = f'{pl_dania(it["dania"])} · ~{gmin}–{gmax} g łącznie'
            else:
                q = fmt_shop(it["ingredient"], it["qty"], it["unit"], d)
            P.append(f'<div class="srow"><input type="checkbox"><label>{esc(cap(it["ingredient"]))}'
                     f'</label><span class="qty">{esc(q)}</span></div>')
        P.append("</div></details>")
    P.append("</div>")

    # ---- Plan tygodnia ----
    P.append("<h2>Plan tygodnia</h2>")
    P.append('<div class="card"><div class="plan">')
    for day in plan["days"]:
        head = f'{esc(day["dow"])} {dm(day["date"])}'
        if day.get("rest"):
            P.append(f'<div class="prow"><div class="pday">{head}</div><div class="pdot rest">'
                     f'</div><div class="pinfo"><div class="prest">{esc(day["rest"])}</div></div></div>')
            continue
        obiady = [recipes[meal_id(r)] for r in day["meals"]
                  if recipes[meal_id(r)].get("type") == "obiad"]
        main = obiady[0] if obiady else recipes[meal_id(day["meals"][0])]
        tag = ""
        if main.get("advance_prep") and "rano" in main["advance_prep"].lower():
            tag = '<span class="ptag">⏰ marynata rano</span>'
        P.append(f'<div class="prow"><div class="pday">{head}</div><div class="pdot"></div>'
                 f'<div class="pinfo"><div class="pdish">{esc(main["name"])}{tag}</div>'
                 f'<div class="pside">{esc(main["_subtitle"])}</div></div></div>')
    P.append("</div></div>")

    # ---- Karty przepisów ----
    P.append("<h2>Przepisy</h2>")
    counter = 0
    for day in plan["days"]:
        for m in day.get("meals", []):
            rid = meal_id(m)
            r = recipes[rid]
            servings = meal_servings(m, plan["servings"])
            scale = servings / r.get("base_servings", 2)
            is_obiad = r.get("type") == "obiad"
            if is_obiad:
                counter += 1
                badge = f'<div class="dcircle">{counter}</div>'
            else:
                badge = '<div class="dcircle sub">+</div>'
            P.append('<div class="recipe"><div class="rhdr">')
            P.append(f'<div class="dbadge"><div class="dname">{esc(day["dow"])} {dm(day["date"])}'
                     f'</div>{badge}</div>')
            sub = r["_subtitle"]
            if servings != plan["servings"]:
                sub = (sub + " · " if sub else "") + f"porcje: {num(servings)}"
            P.append(f'<div><div class="rtitle">{esc(r["name"])}</div>')
            if sub:
                P.append(f'<div class="rside">{esc(sub)}</div>')
            P.append("</div></div>")
            P.append('<div class="rbody">')
            if r.get("advance_prep"):
                P.append(f'<div class="note nwarn">{esc(cap(r["advance_prep"]))}</div>')
            P.append('<div class="slbl">Składniki</div><ul class="ings">')
            for ing in r.get("ingredients", []):
                nm = cap(ing["name"])
                if ing.get("note"):
                    nm += f', {ing["note"]}'
                P.append(f'<li class="ing"><span>{esc(nm)}</span>'
                         f'<span class="iq">{esc(fmt_ing(ing, scale, mrange))}</span></li>')
            if r.get("pantry"):
                P.append(f'<li class="ing"><span>{esc(", ".join(cap(p) for p in r["pantry"]))}</span>'
                         f'<span class="iq">—</span></li>')
            P.append("</ul>")
            steps = r["_steps"]
            if steps:
                P.append('<details class="sacc"><summary>Sposób przygotowania '
                         f'<span class="sc">· {len(steps)} kroków</span> <span class="arr">▸</span>'
                         '</summary><div class="sbody"><ol class="slist">')
                for s in steps:
                    P.append(f"<li>{esc(s)}</li>")
                P.append("</ol></div></details>")
            P.append("</div></div>")

    P.append('<footer>Smacznego!</footer>')
    P.append("</body></html>")
    return "\n".join(P)


# --------------------------------------------------------------------------- #
# Orkiestracja
# --------------------------------------------------------------------------- #
def build_plan(plan_id: str, d: Dictionary, check_only: bool,
               neighbors: tuple = (None, None), profile: dict | None = None) -> list:
    errors: list = []
    plan = load_plan(plan_id)
    recipes: dict[str, dict] = {}
    for day in plan["days"]:
        for m in day.get("meals", []):
            rid = meal_id(m)
            if rid not in recipes:
                try:
                    recipes[rid] = load_recipe(rid)
                except BuildError as e:
                    errors.append(str(e))
    # karty komponentów (mogą nie być osobnym daniem) — dla walidacji typu/serves
    for r in list(recipes.values()):
        for c in r.get("components", []):
            if c not in recipes:
                try:
                    recipes[c] = load_recipe(c)
                except BuildError as e:
                    errors.append(str(e))

    if errors:  # brak kart — nie ma sensu liczyć dalej
        return errors

    mrange = meat_range(profile)
    selftest_classification(*mrange, errors)
    validate_plan(plan, recipes, errors)
    meals_out, demand_out = build_demand(plan, recipes, d, mrange, errors)
    if errors:
        return errors

    demand_json = {
        "plan_id": plan["plan_id"], "revision": plan["revision"], "owner": plan["owner"],
        "period": {"from": str(plan["period"]["from"]), "to": str(plan["period"]["to"])},
        "meals": meals_out, "demand": demand_out,
    }
    out_dir = PLANS_DIR / plan_id
    existing_journal = None
    jpath = out_dir / "journal.json"
    if jpath.exists():
        existing_journal = json.loads(jpath.read_text(encoding="utf-8"))
    journal = build_journal(plan, recipes, existing_journal)
    page = render_html(plan, recipes, demand_out, d, neighbors, mrange)

    if not check_only:
        (out_dir / "demand.json").write_text(
            json.dumps(demand_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jpath.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / "index.html").write_text(page + "\n", encoding="utf-8")
    return errors


def build_manifest() -> list:
    """Manifest tygodni [{plan_id, from, to, url}] z period każdego demand.json.
    Deterministyczny (sort po `from`, bez „dziś") — artefakt zależny wyłącznie od plans/."""
    out = []
    for pid in sorted(p.name for p in PLANS_DIR.iterdir()
                      if p.is_dir() and (p / "plan.yaml").exists()):
        dj = PLANS_DIR / pid / "demand.json"
        if not dj.exists():
            continue
        data = json.loads(dj.read_text(encoding="utf-8"))
        per = data.get("period", {})
        out.append({"plan_id": data["plan_id"], "from": per.get("from"),
                    "to": per.get("to"), "url": f"plans/{data['plan_id']}/"})
    out.sort(key=lambda x: x["from"] or "")
    return out


def write_manifest(manifest: list) -> None:
    (ROOT / "plans.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_root_resolver(manifest: list) -> None:
    """Root: resolver po stronie klienta (data z urządzenia). Reguła: pokrywający dziś
    → najbliższy przyszły → najnowszy. Bez JS / przy błędzie fetch: widoczna lista."""
    items = "\n".join(
        f'  <li><a href="{esc(m["url"])}">{esc(m["plan_id"])} · '
        f'{dm(m["from"])}–{dm(m["to"])}</a></li>' for m in manifest)
    doc = f'''<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan obiadów</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F5F0E8;color:#2A2520;max-width:620px;margin:0 auto;padding:2rem 1rem;font-size:15px;line-height:1.6}}h1{{font-size:20px}}a{{color:#1D9E75;text-decoration:none}}ul{{line-height:2.1;margin-top:.5rem}}</style>
</head><body>
<h1>Plan obiadów</h1>
<p>Otwieram bieżący tydzień… jeśli nie przeskoczy, wybierz z listy:</p>
<ul id="plans">
{items}
</ul>
<script>
fetch('plans.json',{{cache:'no-store'}}).then(function(r){{return r.json();}}).then(function(p){{
  if(!p||!p.length)return;
  p.sort(function(a,b){{return a.from<b.from?-1:a.from>b.from?1:0;}});
  var d=new Date(),t=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  var target=p.filter(function(x){{return x.from<=t&&t<=x.to;}})[0]
           ||p.filter(function(x){{return x.from>t;}})[0]
           ||p[p.length-1];
  if(target)location.replace(target.url);
}}).catch(function(){{}});
</script>
</body></html>
'''
    (ROOT / "index.html").write_text(doc, encoding="utf-8")


def main(argv: list) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("-")]
    d = load_dictionary()
    profile = load_meat_profile()
    lo, hi = meat_range(profile)
    print(f"profil mięsa: przedział dania {lo}–{hi} g (skład: {profile.get('adults', 1)} dorosły "
          f"+ {', '.join(profile.get('children', {}))})")
    all_ids = sorted(p.name for p in PLANS_DIR.iterdir()
                     if p.is_dir() and (p / "plan.yaml").exists())  # pełny zbiór → nawigacja
    plan_ids = args or all_ids
    if not plan_ids:
        print("Brak planów (plans/<id>/plan.yaml).")
        return 1

    all_errors = []
    for pid in plan_ids:
        i = all_ids.index(pid)
        neighbors = (all_ids[i - 1] if i > 0 else None,
                     all_ids[i + 1] if i < len(all_ids) - 1 else None)
        errs = build_plan(pid, d, check_only, neighbors, profile)
        for e in errs:
            all_errors.append(f"[{pid}] {e}")
        status = "OK" if not errs else f"BŁĘDY ({len(errs)})"
        print(f"{'sprawdzono' if check_only else 'zbudowano'} {pid}: {status}")

    if not check_only and not all_errors:
        manifest = build_manifest()
        write_manifest(manifest)
        write_root_resolver(manifest)
        print(f"plans.json + index.html (resolver) ← {len(manifest)} tygodni")

    if all_errors:
        print("\nWalidacja nie przeszła:")
        for e in all_errors:
            print(f"  ✗ {e}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BuildError as e:
        print(f"Błąd: {e}")
        sys.exit(2)
