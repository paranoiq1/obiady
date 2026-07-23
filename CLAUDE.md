# CLAUDE.md — meals

Planer obiadów rodzinnych. Zero backendu — pliki w tym repo SĄ bazą danych, a strona dla żony to statyczny HTML na GitHub Pages. Kontekst obowiązkowy: `README.md` (rejestr decyzji [DECISION]) i `docs/EXTRACT_meals_kickoff.md` (architektura, kontrakt z `expenses`).

## Zasady twarde

- Język: polski w treściach i dokumentach; angielski w kluczach YAML/JSON i w kodzie.
- Składniki wyłącznie kanonicznymi nazwami z `ingredients.md`. Nowy składnik → najpierw wpis w słowniku, potem użycie.
- Karty przepisów: MD + frontmatter YAML wg wzorca z `recipes/`. `base_servings: 2` (przelicznik dorosły = 1, dziecko = 0,5) skaluje **tylko dodatki/węglowodany**. Jedna wersja dania dla wszystkich — bez wariantów per osoba.
- Mięso „daniowe" w kartach: `unit: danie` (nie gramy). Gramaturę liczy `build.py` z **przedziału dania** (profil `meat_profile` w `preferences.md`, obecnie 272–396 g; skład jedzących → przedział). Łosoś na wagę. **Klasyfikacja opakowania W [g]:** największe `n≥1` z `W/n` w przedziale → `n` dań (opakowania = 1 danie nie dzielimy — zasada Moniki); `W < min` → „może zabraknąć"; `W > max` bez podziału → „za dużo — dostosuj albo świadomie więcej (resztki → journal)". Gdy Marcin zgłasza zakup („kupiłem X g"), sklasyfikuj i ostrzeż dokładnie w tym brzmieniu; na liście zakupów podawaj przedział łączny per mięso (dania × przedział).
- Strona planu ma być czysta: bez statusów zakupowych („masz już", „zamówione") i bez śladów odstępstw. Wzorzec markupu i CSS: `plans/2026-W31/index.html` (plik samodzielny, CSS inline).
- `demand.json` = wąski kontrakt do `expenses`: czysta agregacja składników z kart (spiżarnia bazowa poza demandem; `szt` zaokrąglane w górę), `plan_id` = tydzień ISO, zmiany planu przez `revision` (nadpisanie, idempotencja).
- Wykonanie ≠ plan: `plans/<plan_id>/journal.json` (`as_planned` | `swapped` | `replaced` | `skipped` + `note`), KPI „Realizacja planu" agregowane w `kpi.md`.
- Zmiany zasad oznaczaj **[DECISION]** i dopisuj do rejestru w `README.md`; rozjazdy z EXTRACT odnotowuj jako „do rewizji dokumentu".

## Typowe zadania

- **Nowy plan tygodnia:** karty (nowe lub z bazy) → `plans/<ISO>/index.html` + `demand.json` + `journal.json` (pending) → aktualizacja przekierowania w głównym `index.html` → commit.
- **Domknięcie tygodnia:** outcomes w journalu → wiersz w `kpi.md` → wpisy w „Historii i feedbacku" kart.
- **Build:** `python3 build.py` (wymaga `pyyaml`) generuje `plans/<id>/index.html` + `demand.json` + seed `journal.json` z `plan.yaml` + kart + słownika; `--check` waliduje bez zapisu (gate CI). Wejścia edytujesz ręcznie (karty, `plan.yaml`, `ingredients.md`), wyjścia (`index.html`, `demand.json`, `journal.json`) są generowane — nie edytuj ich ręcznie. Nowa jednostka kuchenna → najpierw przelicznik w bloku maszynowym `ingredients.md`. Na push do `main` CI (`.github/workflows/build.yml`) regeneruje i commituje artefakty.
