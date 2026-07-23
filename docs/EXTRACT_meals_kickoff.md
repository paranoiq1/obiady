# EXTRACT — `meals` (planer obiadów) — kickoff nowego projektu

> **Cel dokumentu:** pełny kontekst startowy dla nowego projektu `meals`.
> Wkleić do project knowledge nowego projektu Claude („Obiady").
> Data: lipiec 2026 | Właściciel: Marcin (IT PM, Warszawa)
> Źródło: analiza architektoniczna w projekcie `expenses` (moduł cenowy), sesja 2026-07-22

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
3. Warianty per domownik; feedback po posiłkach zasila bazę
4. Docelowo baza obiadów rosnąca z użycia
5. Output do `expenses`: zapotrzebowanie na produkty do zamówienia
6. Komunikacja między aplikacjami docelowo przez MCP
7. Punkt startowy: czat → HTML → GitHub Pages → żona

---

## 4. RODZINA — wymagania per domownik

| Osoba | Wymaganie |
|---|---|
| Marcin, Monika | dorośli, pełne wersje dań |
| Maja | niejadek — utrzymywać listę „bezpiecznych dań", nowości wprowadzać ostrożnie |
| Marceli | porcja odkładana **PRZED** dodaniem soli i kwaśnych składników (bez przypraw, bez dodanych kwasów) |

Karta przepisu musi umieć opisać wariant per dziecko (moment odłożenia porcji, zamienniki).

---

## 5. KONTRAKT KOMUNIKACYJNY meals → expenses

### 5.1 Artefakt: `demand.json` (jedyny obowiązkowy)

```json
{
  "plan_id": "2026-W31",
  "revision": 2,
  "period": {"from": "2026-07-27", "to": "2026-08-02"},
  "meals": [
    {"date": "2026-07-28", "recipe_id": "kotlety-mielone",
     "servings": 4, "variants": {"marceli": "porcja_bez_soli"}}
  ],
  "demand": [
    {"ingredient": "pierś z kurczaka", "qty": 1.0, "unit": "kg", "type_hint": "B"},
    {"ingredient": "mleko 2%", "qty": 2, "unit": "l", "ean_hint": "5900512320335"}
  ]
}
```

Zasady:
- **Idempotencja:** `plan_id + revision` — ponowna wysyłka nadpisuje, nie duplikuje
- `ean_hint` TYLKO przy lojalności marki (typ A); domyślnie składnik idzie klasą (B/C)
- `type_hint` opcjonalny (A/B/C jak w modelu cenowym `expenses`)
- Ilości zagregowane per plan (agregacja z posiłków po stronie `meals`)

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

### 6.1 Projekt Claude „Obiady" — project knowledge
- `preferences.md` — wynik wywiadu preferencji (lubiane/nielubiane per osoba, bezpieczne dania Mai, reguła Marcelego)
- `ingredients.md` — słownik składników
- szablon planu tygodniowego
- ten dokument (EXTRACT)

### 6.2 Repo GitHub (istniejące, z Pages)

```
recipes/
  kotlety-mielone.md      # karta przepisu (baza obiadów)
plans/
  2026-W31/
    index.html            # strona dla żony (jak dotychczas)
    demand.json           # kontrakt do expenses
preferences.md
ingredients.md
```

Karta przepisu (`recipes/*.md`): składniki (kanoniczne nazwy + ilości na porcję), przygotowanie, warianty dla dzieci, tagi, log ocen/feedbacku.

### 6.3 Rytuał tygodniowy
1. Rozmowa w projekcie „Obiady" → ustalenie menu
2. Claude generuje: `index.html` + `demand.json` + nowe/zmienione karty przepisów
3. Commit → żona przegląda na Pages
4. Feedback wraca do czatu („Maja nie tknęła", ocena 4/5) → aktualizacja kart

### 6.4 Integracja na dziś
`demand.json` wrzucany ręcznie do projektu `expenses`. MCP dopiero gdy `mcp-server` expenses wstanie (jest w kolejce zadań expenses).

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

## 9. OTWARTE PYTANIA

- Format karty przepisu: czysty MD czy MD + frontmatter YAML (łatwiejszy późniejszy parsing)?
- Skalowanie porcji: ilości na porcję (przeliczalne) czy na cały przepis?
- Skala feedbacku: ocena wspólna czy per osoba (Maja osobno)?
- Nazwa repo/domeny: `meals`? (spójnie z konwencją copilota)
- Generowanie HTML: ręcznie przez Claude (MVP) → kiedy przejść na generator statyczny z JSON?
