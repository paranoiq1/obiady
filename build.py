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
import sys, re, json, math, html, unicodedata
from pathlib import Path
import yaml

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


def build_demand(plan: dict, recipes: dict, d: Dictionary, errors: list):
    """Zwraca (meals[], demand[]). Sumuje po jednostce bazowej, pomija spiżarnię."""
    meals_out = []
    totals: dict[str, float] = {}
    for day in plan["days"]:
        for rid in day.get("meals", []):
            r = recipes[rid]
            scale = plan["servings"] / r.get("base_servings", 2)
            meals_out.append({"date": str(day["date"]), "recipe_id": rid,
                              "servings": plan["servings"]})
            for ing in r.get("ingredients", []):
                canon = d.canonical(ing["name"])
                if canon is None:
                    errors.append(f"recipes/{rid}.md: nieznany składnik „{ing['name']}” "
                                  f"(dodaj do ingredients.md)")
                    continue
                if d.by_name[canon]["pantry"]:
                    continue  # spiżarnia bazowa poza demandem
                conv = to_base(d, canon, ing["qty"] * scale, ing["unit"], errors)
                if conv is None:
                    continue
                _, base_qty = conv
                totals[canon] = totals.get(canon, 0.0) + base_qty

    demand_out = []
    for name, meta in d.by_name.items():  # kolejność ze słownika → stabilny diff
        if name in totals:
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
        obiady = [rid for rid in day.get("meals", []) if recipes[rid].get("type") == "obiad"]
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


def fmt_ing(ing: dict) -> str:
    q = frac(float(ing["qty"]))
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
                neighbors: tuple = (None, None)) -> str:
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
        obiady = [recipes[r] for r in day["meals"] if recipes[r].get("type") == "obiad"]
        main = obiady[0] if obiady else recipes[day["meals"][0]]
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
        for rid in day.get("meals", []):
            r = recipes[rid]
            is_obiad = r.get("type") == "obiad"
            if is_obiad:
                counter += 1
                badge = f'<div class="dcircle">{counter}</div>'
            else:
                badge = '<div class="dcircle sub">+</div>'
            P.append('<div class="recipe"><div class="rhdr">')
            P.append(f'<div class="dbadge"><div class="dname">{esc(day["dow"])} {dm(day["date"])}'
                     f'</div>{badge}</div>')
            P.append(f'<div><div class="rtitle">{esc(r["name"])}</div>')
            if r["_subtitle"]:
                P.append(f'<div class="rside">{esc(r["_subtitle"])}</div>')
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
                         f'<span class="iq">{esc(fmt_ing(ing))}</span></li>')
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
               neighbors: tuple = (None, None)) -> list:
    errors: list = []
    plan = load_plan(plan_id)
    recipes: dict[str, dict] = {}
    for day in plan["days"]:
        for rid in day.get("meals", []):
            if rid not in recipes:
                try:
                    recipes[rid] = load_recipe(rid)
                except BuildError as e:
                    errors.append(str(e))

    if errors:  # brak kart — nie ma sensu liczyć dalej
        return errors

    meals_out, demand_out = build_demand(plan, recipes, d, errors)
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
    page = render_html(plan, recipes, demand_out, d, neighbors)

    if not check_only:
        (out_dir / "demand.json").write_text(
            json.dumps(demand_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jpath.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / "index.html").write_text(page + "\n", encoding="utf-8")
    return errors


def latest_plan_id() -> str:
    ids = sorted(p.name for p in PLANS_DIR.iterdir()
                 if p.is_dir() and (p / "plan.yaml").exists())
    return ids[-1]


def write_root_redirect(plan_id: str):
    (ROOT / "index.html").write_text(
        '<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8">\n'
        f'<meta http-equiv="refresh" content="0; url=plans/{plan_id}/">\n'
        '<title>Plan obiadów</title></head>\n'
        f'<body><p>Aktualny plan: <a href="plans/{plan_id}/">{plan_id}</a></p></body></html>\n',
        encoding="utf-8")


def main(argv: list) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("-")]
    d = load_dictionary()
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
        errs = build_plan(pid, d, check_only, neighbors)
        for e in errs:
            all_errors.append(f"[{pid}] {e}")
        status = "OK" if not errs else f"BŁĘDY ({len(errs)})"
        print(f"{'sprawdzono' if check_only else 'zbudowano'} {pid}: {status}")

    if not check_only and not all_errors:
        latest = latest_plan_id()
        write_root_redirect(latest)
        print(f"index.html → plans/{latest}/")

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
