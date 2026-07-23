# KPI planowania obiadów — `kpi.md`

Cel: odpowiedzieć na pytanie, **czy układanie menu ma sens** — czyli czy zaplanowane (i kupione) obiady faktycznie trafiają na stół.

## Definicje

Źródło danych: `plans/<plan_id>/journal.json` (wykonanie) porównane z `meals[]` z `demand.json` (rewizja wskazana w `baseline_revision`, obowiązująca w momencie zakupów).

Dzień obiadowy = unikalna data w `meals[]`. Danie główne (`type: obiad`) reprezentuje dzień; komponenty i dodatki (`sos`, `chrupiąca ciecierzyca`) podążają za nim i nie liczą się osobno.

Wynik dnia (`outcome` w journalu):

| outcome | Znaczenie |
|---|---|
| `as_planned` | ugotowane zgodnie z planem i dniem |
| `swapped` | danie z planu, inny dzień (zakupy wykorzystane) |
| `replaced` | inne danie niż planowane — `actual` = id karty z bazy lub krótki opis |
| `skipped` | nic z planu (np. nieplanowane jedzenie na mieście) |

**Realizacja planu = (as_planned + swapped) / dni obiadowe.** Zamiana dnia to sukces planowania — kupione zostało ugotowane, dzień jest szczegółem. Pomocniczo raportujemy zgodność co do dnia (sam `as_planned`).

Pole `note` w journalu zbiera powody odstępstw — po kilku tygodniach to z niego wyjdą wnioski jakościowe (np. „środy są za ciasne na marynatę").

## Wyniki

| Tydzień | Dni | Zgodnie | Zamiany | Podmiany | Odpuszczone | Realizacja | Zgodność dnia |
|---|---|---|---|---|---|---|---|
| _(pierwszy wiersz po zamknięciu 2026-W31)_ | | | | | | | |

Próg interpretacji („poniżej X% planowanie nie ma sensu") — do ustalenia po 3–4 tygodniach danych.
