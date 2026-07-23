# meals — planer obiadów rodzinnych (MVP)

Formalizacja obecnego workflow: czat → HTML → GitHub Pages → żona. Zero backendu, zero bazy danych. Osobna domena, wąski kontrakt z `expenses` przez `demand.json`. Źródło prawdy architektury: `EXTRACT_meals_kickoff.md` (project knowledge).

## Struktura

Legenda: **[wej]** = źródło prawdy (edytujesz ręcznie), **[gen]** = generowane przez `build.py` (nie edytuj ręcznie).

```
CLAUDE.md                 # zasady pracy dla sesji Claude Code
build.py                  # [wej] generator: plan.yaml + karty + słownik → index.html + demand.json + journal.json
index.html                # [gen] przekierowanie na bieżący plan (stała zakładka dla żony)
.github/workflows/
  build.yml               # CI: walidacja na PR, regeneracja + commit na push do main
docs/
  EXTRACT_meals_kickoff.md  # architektura i kontrakt (kopia dokumentu źródłowego)
recipes/                  # [wej] baza obiadów — karty przepisów (MD + frontmatter YAML)
plans/
  2026-W30/               # jeden katalog na tydzień (id = tydzień ISO startu)
    plan.yaml             # [wej] źródło planu tygodnia (dni, dania, rewizja)
    index.html            # [gen] strona dla żony (samodzielny plik, CSS inline)
    demand.json           # [gen] kontrakt do expenses
    journal.json          # [gen seed] rejestr wykonania; wyniki dopisywane ręcznie (build nie nadpisuje)
preferences.md            # [wej] preferencje rodziny (SZKIC — czeka na wywiad)
ingredients.md            # [wej] słownik składników (kanoniczne nazwy ≈ klasy W3) + blok maszynowy konwersji
kpi.md                    # [wej] KPI realizacji planów (agregat tygodniowy)
```

## Build

`python3 build.py` (wymaga `pyyaml`) czyta `plans/<id>/plan.yaml` + karty `recipes/` + słownik `ingredients.md` i generuje dla każdego planu `index.html` + `demand.json` + seed `journal.json`, a w korzeniu — przekierowanie na najnowszy plan. `python3 build.py 2026-W31` buduje jeden plan; `python3 build.py --check` waliduje bez zapisu (nazwy kanoniczne + przeliczalność jednostek) i zwraca niezerowy kod przy błędzie — to jest gate w CI. Na push do `main` workflow regeneruje artefakty i commituje je z powrotem (`[skip ci]`), więc **strona buduje się sama** po edycji karty lub `plan.yaml`.

## Rytuał tygodniowy

1. Rozmowa w projekcie „Obiady" → ustalenie menu (z użyciem `preferences.md` i bazy `recipes/`).
2. Nowe/zmienione karty w `recipes/` + `plans/<plan_id>/plan.yaml` → `python3 build.py` regeneruje `index.html` + `demand.json` + seed `journal.json`.
3. Commit → CI waliduje/regeneruje → żona przegląda na Pages.
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
- **[DECISION] `build.py` = statyczny generator (zamyka otwarte pytanie EXTRACT §9).** Ręczne pisanie `index.html` zastąpione generacją z danych. `index.html`, `demand.json`, `journal.json` są odtąd artefaktami **[gen]** — edytujemy wejścia (karty, `plan.yaml`, słownik), nie wyjścia. Zero zależności poza `pyyaml`. Skutek uboczny akceptowany: strona odtwarzana z danych różni się kosmetycznie od poprzedniej ręcznej wersji (sos renderowany jako osobna karta z badge „+", opisy ilości wyliczane, nie redakcyjne).
- **[DECISION] `plan.yaml` = źródło prawdy planu tygodnia.** `demand.json` to **wyjście** (kontrakt do `expenses`), więc nie może być zarazem wejściem — plan (dni, dania, dni wolne, `revision`) mieszka w `plans/<id>/plan.yaml`. `meals[]` w `demand.json` jest z niego generowane.
- **[DECISION] Blok maszynowy w `ingredients.md`.** Tabele pozostają źródłem nazw/jednostek/spiżarni; dołożony blok ```yaml``` z przelicznikami jednostek kuchennych na bazowe (`ząbek`→główka 0,25; `łyżka` jogurtu ≈ 25 g, bułki tartej ≈ 11 g; `g`/`ml` → 0,001) i etykietami opakowań na listę zakupów. Nowa jednostka → najpierw wpis tutaj.
- **[DECISION] Pakowane składniki liczone w `szt`** (puszka, tacka): karty wyrażają zużycie jako ułamek `szt` (ciecierzyca ½ + ½ = 1 puszka), nie w gramach — inaczej sumowanie po wadze rozjeżdża liczbę opakowań. Zaokrąglenie w górę zostaje.
- **[DECISION] Komponenty nie są automatycznie rozwijane w demandzie.** Gdy komponent trzeba osobno kupić/ugotować (sos, chrupiąca ciecierzyca), planer wpisuje go jako osobny `meal` w `plan.yaml`; pole `components` w kartach to referencja dla człowieka/UI, nie mnożnik zapotrzebowania (inaczej podwójne liczenie).
- **[DECISION] CI jako gate + auto-build.** `.github/workflows/build.yml`: na PR wyłącznie `build.py --check` (blokuje niekanoniczne nazwy / nieprzeliczalne jednostki); na push do `main` regeneracja i commit artefaktów z `[skip ci]`. Pages serwuje z gałęzi — bez zmiany ustawień repo. Warunki bezpieczeństwa commit-backu: (a) push domyślnym `GITHUB_TOKEN` — nie wyzwala kolejnych workflowów, brak pętli (PAT by zapętlił); (b) `permissions: contents: write`; (c) `build.py` deterministyczny (bez timestampów) i commit **tylko przy realnej różnicy** (`git diff --cached --quiet` → skip), żeby historia nie puchła od pustych runów.
- **[DECISION] Artefakty nie są równe: zapisy vs widok.** `demand.json` (kontrakt z rewizjami) i `journal.json` (wykonanie) to **zapisy** — commitowane zawsze, także w wariancie docelowym. `index.html` to **widok** — jedyny kandydat do `.gitignore`, gdy kiedyś przejdziemy na deploy przez Actions. Bonus obecnego podejścia (commit-back): strony historycznych tygodni zostają zamrożone dokładnie tak, jak widziała je żona, podczas gdy `deploy-pages` renderowałby przeszłość bieżącym szablonem. Wniosek: **commit-back może zostać na dłużej — presja na przełączanie niska.**
- **[DECISION] `plan_id` ściśle wg ISO (bez luźnej numeracji).** Id planu = tydzień ISO daty startowej (`2026-W30` dla startu 23.07). Pierwotny „W31" dla 24.07 był błędny (to ISO W30) — skorygowane. Plany przejściowo dłuższe (np. 23.07–02.08) zachowują id tygodnia startowego. Root `index.html` przekierowuje na plan o najwyższym id (leksykograficznie = najnowszy).
- **[DECISION] Nawigacja tydzień ← →.** Nagłówek każdej strony ma linki „‹ poprzedni / następny ›" do sąsiednich planów (po `plan_id`), wyłączone gdy sąsiada brak. Generowane przez `build.py` z pełnego zbioru `plans/*/plan.yaml` — nie trzeba przebudowywać wszystkich stron ręcznie, ale zmiana zbioru planów wymaga rebuildu (CI robi to na push).
- ~~**[DECISION] Porcja mięsa = 200 g/osobę; danie = 400 g** (sztywny nominał)~~ → **uchylone migracją 02** (sztywne nominały nie działały: cała tacka za dużo, połówka za mało). Zastąpione przedziałami poniżej.
- **[DECISION] Przedziały mięsa per danie** (migracja 02). Profil w `preferences.md` (`meat_profile`): dorosły 170–220 g; mnożnik 0,3–0,4× per dziecko (definiowalny — dzieci rosną). Przedział dania liczony ze składu jedzących: `[adult_min × (adults + Σ min), adult_max × (adults + Σ max)]` = obecnie **272–396 g** (~290–400 g). Zastępuje sztywne nominały per mięso; mięso w kartach = `unit: danie`, łosoś na wagę.
- **[DECISION] Klasyfikacja opakowania.** Największe `n≥1` z `W/n` w przedziale → `n` dań; opakowania sklasyfikowanego jako 1 danie **nie dzielimy** (zasada Moniki); `W < min` → ostrzeżenie „może zabraknąć mięsa"; `W > max` bez podziału → „za dużo — dostosuj albo świadomie więcej" (świadome więcej ⇒ resztki → `leftovers` w journalu). Algorytm w `build.py` (`classify_package`) z wektorami testowymi jako bramką.
- **[DECISION] Batch mielone = 2 dania zakupowo** (≈ 580–790 g łącznie); uchyla podział pojedynczej tacki pół na pół. **Zamrażarka jest** (koryguje założenie migracji 02) → rozkład w czasie swobodny: kotlety dziś, drugą porcję (surową lub jako sos) można zamrozić. **Sos rozprzężony** — osobne, opcjonalne danie (składnik-bazowy), nie wymuszone tego samego dnia co kotlety.
- **[DECISION] Demand mięsa: `qty` = środek przedziału łącznego (kg) + `qty_range: [min, max]`** (+ `dania`) — pola dodatkowe kontraktu (expenses ignoruje nieznane). Klasyfikacja zakupu po stronie meals przy raporcie „kupiłem X g".
- **[DECISION] Override porcji per danie** (`meals: [{ id: ..., servings: N }]`). Pozwala zrobić jedno danie większe/mniejsze bez ruszania reszty planu — batch „na zapas" (pulpeciki `servings: 3` = 600 g, część do zamrożenia) albo lżejszy dzień. `build.py` skaluje ilości na stronie i w `demand.json`; karta pokazuje „porcje: N".
- **[DECISION] Sos rozprzężony od kotletów.** Zdjęta naleciałość „mielone = od razu sos tego samego dnia": `kotlety-mielone` bez wymuszonego `advance_prep`, sos to osobne, opcjonalne danie robione, gdy jest potrzebne (np. pod makaron). Karta sosu: batch opcjonalny, lodówka 3–4 dni lub zamrożenie.
- **[DECISION] Walidacja spójności planu w `build.py` (gate CI).** Poza nazwami kanonicznymi i jednostkami `--check` sprawdza: (a) etykieta dnia zgodna z kalendarzem; (b) dni w okresie planu; (c) **przepływ komponentów** — danie-konsument (`components: [<składnik-bazowy>]`, np. makaron→sos) musi mieć bazę w planie, ugotowaną **nie później** niż dzień konsumpcji, a batch(e) muszą pokryć liczbę dań-konsumentów. Pojemność bazy = pole `serves` na karcie (ile dań karmi jeden batch; sos `serves: 2`). Łapie „makaron w dodatkowy dzień, a sos się nie wyrabia" (sam makaron bez mięsa).
- **[DECISION] Mrożenie dozwolone; strategia przy psuciu = „zrób więcej i zamroź".** Zniesione dawne „brak zamrażarki" w `ingredients.md` (łopatka). Gdy świeże mięso (np. 4-dniowa ważność) nie zmieści się w oknie, planer robi większy batch dania mrożalnego (sos, pulpeciki, kotlety) zamiast wyrzucać — zamiast wpychać nadmiar w napięty grafik.

## Otwarte pytania (pozostałe z EXTRACT §9)

- Skala feedbacku: ocena wspólna czy per osoba?
- Nazwa repo: `meals` vs obecne `obiady` (Pages).
- ~~Kiedy przejść z ręcznej generacji HTML na generator statyczny~~ → zamknięte: `build.py` (patrz rejestr wyżej).
- Deploy Pages przez GitHub Actions zamiast serwowania [gen] z gałęzi — niski priorytet (patrz decyzja „zapisy vs widok"). Gdy przyjdzie pora: jednorazowo Settings → Pages → Build and deployment → Source: „GitHub Actions", potem `actions/upload-pages-artifact` + `actions/deploy-pages` i koniec commitowania `index.html`; `demand.json`/`journal.json` nadal commitowane.
