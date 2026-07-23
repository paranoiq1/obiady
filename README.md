# meals — planer obiadów rodzinnych (MVP)

Formalizacja obecnego workflow: czat → HTML → GitHub Pages → żona. Zero backendu, zero bazy danych. Osobna domena, wąski kontrakt z `expenses` przez `demand.json`. Źródło prawdy architektury: `EXTRACT_meals_kickoff.md` (project knowledge).

## Struktura

```
CLAUDE.md                 # zasady pracy dla sesji Claude Code
index.html                # przekierowanie na bieżący plan (stała zakładka dla żony)
docs/
  EXTRACT_meals_kickoff.md  # architektura i kontrakt (kopia dokumentu źródłowego)
recipes/                  # baza obiadów — karty przepisów (MD + frontmatter YAML)
plans/
  2026-W31/
    index.html            # strona dla żony (samodzielny plik, CSS inline)
    demand.json           # kontrakt do expenses
    journal.json          # rejestr wykonania (zamiany, podmiany, odpuszczone)
preferences.md            # preferencje rodziny (SZKIC — czeka na wywiad)
ingredients.md            # słownik składników (kanoniczne nazwy ≈ klasy W3)
kpi.md                    # KPI realizacji planów (agregat tygodniowy)
```

## Rytuał tygodniowy

1. Rozmowa w projekcie „Obiady" → ustalenie menu (z użyciem `preferences.md` i bazy `recipes/`).
2. Claude generuje: `plans/<plan_id>/index.html` + `demand.json` + nowe/zmienione karty przepisów.
3. Commit → żona przegląda na Pages.
4. Feedback wraca do czatu → oceny do „Historii i feedbacku" w kartach; odstępstwa wykonania (zamiany, podmiany, odpuszczone) do `journal.json`; wiersz KPI do `kpi.md`.
5. `demand.json` wrzucany ręcznie do projektu `expenses` (bridge do czasu MCP).

## Format karty przepisu

Frontmatter YAML (klucze EN, wartości PL) + treść PL. Pola: `id`, `type` (obiad / składnik-bazowy / dodatek), `base_servings`, `advance_prep`, `components` (referencje do innych kart), `ingredients` (wyłącznie nazwy kanoniczne ze słownika), `pantry` (spiżarnia bazowa — poza demand). Sekcje treści: Przygotowanie · Historia i feedback. Jedna wersja dania — bez wariantów per osoba.

## Decyzje (rejestr — do zatwierdzenia przez Marcina)

- **[DECISION] Jedna wersja dania dla wszystkich.** Bez osobnego traku dla Marcelego — karty i strona bez pól/sekcji wariantów. Uchyla wymaganie z EXTRACT §4 („warianty per domownik", reguła odkładania porcji) — EXTRACT do aktualizacji przy najbliższej rewizji dokumentu.
- **[DECISION] Przelicznik porcji: dorosły = 1, dziecko = 0,5.** Marcin (1) + Maja (0,5) + Marceli (0,5) = `base_servings: 2` dla wszystkich kart i planów. Ilości w przepisach bez zmian — zmiana księgowa (ten sam skład wcześniej liczony jako 1,5).
- **[DECISION] `plan_id` = tydzień ISO** (`2026-W31`). Pierwszy plan przejściowo dłuższy: 24.07–02.08; kolejne czysto pn–nd. Domknięcie dni 31.07–02.08 = `revision: 2` (nadpisanie, nie duplikat — zgodnie z idempotencją kontraktu).
- **[DECISION] `demand[]` = czysta agregacja składników z kart planu.** Bez odejmowania spiżarni, bez buforów, bez statusów zamówień („już masz", „zamówione" nie występują). Zaokrąglenia: jednostki `szt` w górę do pełnych sztuk; miary łyżkowe → przybliżenia wagowe. Spiżarnia bazowa (przyprawy, tłuszcze) poza demandem. Odejmowanie spiżarni = faza 2 po stronie `expenses` (zwrotka „już masz").
- **[DECISION] Karta = MD + frontmatter YAML.** Składniki maszynowo w frontmatter (jedno źródło prawdy → przyszła generacja `demand.json` i HTML), treść dla ludzi w body.
- **[DECISION] Ilości na cały przepis + jawne `base_servings`.** Przeliczalne, a liczby pozostają „kuchenne" (1 tacka, 1 torebka).
- **[DECISION] Komponenty wielokrotnego użytku jako osobne karty** (`sos-pomidorowy-z-mielonym`, `chrupiaca-ciecierzyca`) z polem `components` w kartach-konsumentach.
- **[DECISION] Rejestr wykonania: `plans/<plan_id>/journal.json`.** Wpis per dzień obiadowy (danie główne reprezentuje dzień): `planned` / `actual` / `outcome` (`as_planned` | `swapped` | `replaced` | `skipped`) + opcjonalna `note` z powodem. Seedowany z planu ze stanem `pending`, wypełniany na kolejnej sesji z relacji Marcina. `baseline_revision` wskazuje rewizję, względem której liczymy KPI.
- **[DECISION] KPI „Realizacja planu"** = (as_planned + swapped) / dni obiadowe; pomocniczo zgodność co do dnia. Definicje i agregat tygodniowy w `kpi.md`. Wymaganie spoza EXTRACT — dopisać przy rewizji dokumentu.
- **[DECISION] Zamiany a rewizje:** zmiana przyszłego harmonogramu lub menu = rewizja planu (`meals[]`/`demand[]`, revision+1) + regeneracja strony; to, co faktycznie ugotowano, trafia wyłącznie do journala. Strona dla żony bez śladów odstępstw.
- Domyślny typ dopasowania w `expenses`: **B** — `type_hint` pomijamy; `ean_hint` dopiero przy lojalności marki.

## Otwarte pytania (pozostałe z EXTRACT §9)

- Skala feedbacku: ocena wspólna czy per osoba?
- Nazwa repo: `meals` vs obecne `obiady` (Pages).
- Kiedy przejść z ręcznej generacji HTML na generator statyczny z frontmatter + JSON.
