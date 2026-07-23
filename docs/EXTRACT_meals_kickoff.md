# EXTRACT — `meals` (planer obiadów) — kickoff nowego projektu

> **Cel dokumentu:** pełny kontekst startowy dla nowego projektu `meals`.
> Wkleić do project knowledge nowego projektu Claude („Obiady").
> Data: lipiec 2026 (kickoff) · **rev 2: 2026-07-23** (konsolidacja) | Właściciel: Marcin (IT PM, Warszawa)
> Źródło: analiza architektoniczna w projekcie `expenses` (moduł cenowy), sesja 2026-07-22

> **rev 2 — konsolidacja rozjazdów kickoffu z decyzjami z realizacji.** Żywy rejestr decyzji to `README.md` (markery [DECISION]); EXTRACT nie duplikuje pełnej listy, tylko prostuje założenia, które się zdezaktualizowały. Główne korekty: **jedna wersja dania** — bez wariantów per osoba (§3–§4); **model mięsa przedziałowy** + klasyfikacja opakowań (§4–§5); **zamrażarka jest** (§6); **rejestr wykonania `journal.json` + KPI realizacji** (§6); **format karty i generator rozstrzygnięte** (§9). Zmiany rev 2 oznaczone `[rev2]`.

---

## 1. CO BUDUJEMY

Aplikacja `meals` — planer obiadów rodzinnych. **Osobna domena i osobne repo, NIE moduł `expenses`.**

**Trzy funkcje rdzeniowe:**
1. Konwersacyjne planowanie menu tygodniowego (czat ustala obiady, generuje sposób przygotowania i zapotrzebowanie na składniki)
2. Rosnąca baza obiadów (karty przepisów + historia planów + feedback rodziny)
3. Eksport zapotrzebowania do `expenses` (kontrakt `demand.json` → docelowo MCP)

**Stan obecny (punkt startowy):** rozmowa w czacie → Claude generuje stronę HTML → GitHub Pages → żona przegląda. To formalizujemy, nie zastępujemy.

---

## 2. RELACJA DO EXPENSES — granica domen

Najważniejsze decyzje architektoniczne, podjęte przed startem:

**[DECISION] `meals` = osobna aplikacja, wąski kontrakt z `expenses`.**
Zgodnie z zasadą copilota: multi-repo, każdy serwis = własne repo + MCP server jako warstwa dostępu do danych.

**[DECISION] Podział języków domen:**
- `meals` mówi językiem **składników** (nazwa kanoniczna + ilość + jednostka). Nigdy EAN-ami, nigdy cenami.
- `expenses` tłumaczy: składnik → klasa W3 → ranking produktów W1/W2 (typ B: najtańszy per cena jednostkowa) → lista zakupów / zamówienie.
- Kluczowa obserwacja: **składnik kulinarny ≈ klasa rodzajowa W3** („mleko 2%", „pierś z kurczaka" to dokładnie klasy z modelu cenowego).

**[DECISION] Zero dublowania danych:**
- `meals` NIE przechowuje produktów, EAN-ów, cen ani katalogów sklepów
- `expenses` NIE przechowuje przepisów, planów ani preferencji rodziny
- F-60/M6-lite w `expenses` = „demand ingest + resolver" (przyjęcie i rozwiązanie `demand.json`), NIE moduł przepisów

**Synergia (faza 2, nie MVP):** koszt obiadu/planu, „to już masz" ze spiżarni (historia zakupów) — jako zwrotka przez MCP `expenses`, nie przez wcielenie jednej aplikacji w drugą.

---

## 3. WSTĘPNE ZAŁOŻENIA (od Marcina)

1. Planowanie konwersacyjne — czat ustala menu, sposób przygotowania, listę składników
2. Wywiad preferencji na starcie (wzorzec z Asystenta Widoczności Zawodowej): co kto lubi / nie lubi, ulubione potrawy, linki do przepisów
3. ~~Warianty per domownik~~ → `[rev2]` **jedna wersja dania dla wszystkich** (bez traku per osoba); feedback po posiłkach zasila bazę
4. Docelowo baza obiadów rosnąca z użycia
5. Output do `expenses`: zapotrzebowanie na produkty do zamówienia
6. Komunikacja między aplikacjami docelowo przez MCP
7. Punkt startowy: czat → HTML → GitHub Pages → żona

---

## 4. RODZINA — wymagania per domownik

`[rev2]` **Jedna wersja dania dla wszystkich — bez wariantów per osoba** (uchyla pierwotne „porcja Marcelego odkładana przed solą" i „karta musi opisać wariant per dziecko"). Różnice ujmujemy **ilościowo**, nie jako osobne traki:

| Osoba | Ujęcie |
|---|---|
| Marcin, Monika | dorośli — pełna porcja (przelicznik = 1) |
| Maja | dziecko — przelicznik 0,5 (dodatki); niejadek: lista „bezpiecznych dań", nowości ostrożnie |
| Marceli | dziecko — przelicznik 0,5 (dodatki) |

**Model porcji `[rev2]`:** `base_servings` (dorosły 1 / dziecko 0,5) skaluje **tylko dodatki/węglowodany**. **Mięso** ma osobny **profil przedziałowy** (`meat_profile` w `preferences.md`: dorosły 170–220 g, mnożnik dziecka 0,3–0,4× — definiowalny) → **przedział dania** (obecnie 272–396 g) + **klasyfikacja opakowań** (patrz §5 i `README.md`). Skład jedzących → przedział (Monika przy stole przelicza).

---

## 5. KONTRAKT KOMUNIKACYJNY meals → expenses

### 5.1 Artefakt: `demand.json` (jedyny obowiązkowy)

```json
{
  "plan_id": "2026-W31",
  "revision": 2,
  "period": {"from": "2026-07-27", "to": "2026-08-02"},
  "meals": [
    {"date": "2026-07-28", "recipe_id": "kotlety-mielone", "servings": 2}
  ],
  "demand": [
    {"ingredient": "łopatka mielona wieprzowa", "qty": 0.67, "unit": "kg",
     "qty_range": [0.54, 0.79], "dania": 2},
    {"ingredient": "makaron fusilli", "qty": 0.15, "unit": "kg"}
  ]
}
```

Zasady:
- **Idempotencja:** `plan_id + revision` — ponowna wysyłka nadpisuje, nie duplikuje
- `[rev2]` **Bez `variants` per osoba** (jedna wersja dania). `meals[]` niosą `servings` (możliwy override per danie).
- `[rev2]` **Mięso „daniowe":** `qty` = środek przedziału łącznego (kg) + `qty_range: [min,max]` + `dania`; klasyfikacja opakowania po stronie `meals`. Reszta składników — waga/szt.
- `ean_hint` TYLKO przy lojalności marki (typ A); domyślnie składnik idzie klasą (B/C). `type_hint` opcjonalny.
- Ilości zagregowane per plan (agregacja z kart po stronie `meals`; pola dodatkowe expenses ignoruje).

### 5.2 Słownik składników — `ingredients.md`

Kanoniczne nazwy składników = odpowiednik W3 po stronie `meals`.
Bez tego „pierś z kurczaka" vs „filet z kurczaka" rozjedzie matching.
Każdy przepis referencuje wyłącznie nazwy ze słownika; nowy składnik = najpierw wpis do słownika.

### 5.3 Zwrotka expenses → meals (faza 2, nie MVP)

- status dopasowań per składnik (matched / unmatched / ambiguous)
- wybrany produkt + cena → koszt posiłku i planu
- pozycje „już masz" (spiżarnia z historii zakupów)

### 5.4 Transport

| Etap | Mechanizm |
|---|---|
| MVP | plik `demand.json` w repo, konsumowany ręcznie w `expenses` (bridge jak `decisions/`) |
| Docelowo | tool-e na MCP `expenses`: `submit_demand(plan)`, `get_demand_status(plan_id)`, `get_plan_cost(plan_id)` |
| Docelowo | `meals` wystawia własny MCP dla agenta centralnego: `get_recipes()`, `get_current_plan()` |

**Tożsamość:** `owner` spójny z `expenses` (`marcin` / `monika`).

---

## 6. MVP — zero backendu

Formalizacja obecnego workflow. Żadnej bazy danych, żadnego serwera.

`[rev2] Zamrażarka: gospodarstwo JĄ MA` — uchyla założenie „brak zamrażarki" z kickoffu. Status bieżący (np. „w naprawie" → mrożenie niedostępne) trzyma `preferences.md`; przy niedostępnej: nadwyżki → lodówka + `leftovers` w journalu, mielone na 2 dania tego samego dnia.

### 6.1 Wiedza projektu (w repo, nie „w pamięci rozmów")
- `preferences.md` — preferencje + `meat_profile` (profil mięsa) + status zamrażarki `[rev2]`
- `ingredients.md` — słownik składników + blok maszynowy konwersji jednostek
- `plans/<ISO>/plan.yaml` — `[rev2]` **źródło prawdy planu tygodnia** (wejście generatora)
- ten dokument (EXTRACT)

### 6.2 Repo GitHub (Pages) — stan rev 2

```
build.py                  # [rev2] generator: plan.yaml + karty + słownik → index.html + demand.json + journal.json
index.html                # [gen] root: resolver client-side (wybiera tydzień z plans.json)
plans.json                # [gen] manifest tygodni
.github/workflows/build.yml  # [rev2] CI: walidacja na PR, regeneracja na push
docs/
  EXTRACT_meals_kickoff.md
  migrations/             # [rev2] migracje modelu (np. przedziały mięsa)
recipes/*.md              # baza obiadów — karty (MD + frontmatter YAML)
plans/<ISO>/
  plan.yaml               # [wej] źródło planu
  index.html              # [gen] strona dla żony (samodzielna, CSS inline)
  demand.json             # [gen] kontrakt do expenses
  journal.json            # [gen seed] rejestr wykonania (wyniki dopisywane ręcznie)
preferences.md · ingredients.md · kpi.md
```

`[rev2]` **Karta przepisu** = MD + **frontmatter YAML** (rozstrzygnięcie §9). Pola: `id`, `type` (obiad / składnik-bazowy / dodatek), `base_servings`, `advance_prep`, `components`, `serves` (ile dań karmi jeden batch bazy), `ingredients` (nazwy kanoniczne; mięso daniowe `unit: danie`, reszta waga/szt), `pantry` (spiżarnia poza demandem). Treść: przygotowanie · historia/feedback. **Bez sekcji wariantów per dziecko.**

### 6.3 Rytuał tygodniowy `[rev2]`
1. Rozmowa → ustalenie menu (z `preferences.md` i bazy `recipes/`)
2. Edycja wejść: karty `recipes/` + `plans/<ISO>/plan.yaml` → `python3 build.py` regeneruje `index.html` + `demand.json` + seed `journal.json` (+ `plans.json`, root)
3. Commit → CI waliduje/regeneruje → żona przegląda na Pages (root sam wybiera bieżący tydzień)
4. Feedback → oceny do „Historii" kart; odstępstwa wykonania → `journal.json`; wiersz KPI → `kpi.md`

### 6.4 Wykonanie ≠ plan `[rev2]`
Rejestr wykonania `plans/<plan_id>/journal.json` (`as_planned` | `swapped` | `replaced` | `skipped` + `note`, „świadomie więcej" → `leftovers`). KPI „Realizacja planu" = (as_planned + swapped) / dni obiadowe, agregat w `kpi.md`. Walidacja spójności planu (przepływ komponentów, kalendarz, klasyfikacja mięsa) w `build.py --check` — gate CI.

### 6.5 Integracja na dziś
`demand.json` wrzucany ręcznie do projektu `expenses`. MCP dopiero gdy `mcp-server` expenses wstanie (kolejka zadań expenses).

---

## 7. ZASADY PRACY (przeniesione z copilota — respektować)

- **Waterfall / dokumentacja przed kodem** — dokument jest źródłem prawdy
- **Decision register** — decyzje architektoniczne zapisywane z markerem [DECISION]
- **Database over hardcode** — tu: słownik i karty w repo, nie „w pamięci rozmów"
- Język: **polski w rozmowie i dokumentach, angielski w kodzie i schematach JSON**
- Feedback bezpośredni, korekta bez defensywności

---

## 8. PIERWSZA SESJA NOWEGO PROJEKTU — plan

1. **Wywiad preferencji** (wzorzec AW): per osoba lubiane/nielubiane, ulubione potrawy, linki do przepisów, produkty zakazane/ograniczone → `preferences.md`
2. Start `ingredients.md` — zaczątek słownika z pierwszych przepisów
3. Format karty przepisu — ustalić strukturę na 1–2 przykładach z dotychczasowych obiadów
4. Pierwszy pełny cykl: plan tygodnia → HTML + `demand.json` → commit

---

## 9. OTWARTE PYTANIA — stan rev 2

Rozstrzygnięte (szczegóły w rejestrze [DECISION] w `README.md`):
- ~~Format karty~~ → **MD + frontmatter YAML** `[rev2]`.
- ~~Skalowanie porcji~~ → **ilości na cały przepis + `base_servings`** dla dodatków; **mięso przedziałem** z profilu `[rev2]`.
- ~~Generowanie HTML~~ → **`build.py`** (generator statyczny) + CI `[rev2]`.

Nadal otwarte:
- Skala feedbacku: ocena wspólna czy per osoba (Maja osobno)?
- Nazwa repo/domeny: obecnie `obiady` (Pages) vs docelowe `meals` (konwencja copilota).
- Zamrażarka: po naprawie flip statusu w `preferences.md` (bez migracji).
