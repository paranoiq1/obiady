# Migracja 02: przedziały mięsa per danie + klasyfikacja opakowań

Instrukcja dla sesji Claude Code w repo `meals`. Wykonaj jako **jeden commit**. Wymaga wcześniejszej migracji `2026-07-23-danie-sides` (anchor w daniach) — jeśli niezastosowana, najpierw ją. Repo żyje: weryfikuj stan plików przed edycją, cel jest deklaratywny. Plik migracji zapisz w `docs/migrations/`.

## Kontekst

Sztywne nominały mięsa per danie (poprzednia migracja) nie działają: tacka 400 g gotowana w całości dała za dużo, a jej połówka (200 g) to za mało — Monika słusznie nie dzieli tacki mieszczącej się „mniej więcej w porcji". Zastępujemy nominały **przedziałem dania** liczonym z konfigurowalnego profilu oraz **algorytmem klasyfikacji opakowania**.

## Model docelowy

**Profil porcji mięsa** (w `preferences.md`, konfigurowalny):
- dorosły: **170–220 g** mięsa na danie,
- dziecko: mnożnik **0,3–0,4×** per dziecko — wartości definiowalne osobno dla każdego dziecka (dzieci rosną, aktualizować przy okazji wywiadów/feedbacku).

**Przedział dania** dla składu jedzącego = `[adult_min × (1 + Σ mnożniki_min), adult_max × (1 + Σ mnożniki_max)]`.
Obecny skład (Marcin + Maja + Marceli): `[170 × 1,6; 220 × 1,8]` = **272–396 g** (prezentacyjnie: ~290–400 g). Zmiana składu (np. Monika przy stole) lub mnożników → przedział przelicza się z profilu, nie jest zahardkodowany.

**Klasyfikacja opakowania o wadze W** (dla mięsa objętego daniami; łosoś na wagę — poza tym):
1. Znajdź największe `n ≥ 1`, dla którego `W/n` mieści się w przedziale → **W = n dań**, OK. Opakowania sklasyfikowanego jako 1 danie **nie dzielimy** (zasada Moniki).
2. Brak takiego `n` i `W < min` → ostrzeżenie **„może zabraknąć mięsa"**.
3. Brak takiego `n` i `W > max` → ostrzeżenie **„za dużo — dostosuj ilość albo świadomie przygotuj więcej"** (świadome więcej ⇒ spodziewane resztki → `leftovers` w journalu).

Wektory testowe (do przyszłego `build.py`/`check.py` i do sekcji Akceptacja):

| W [g] | Wynik |
|---|---|
| 200 | ZA MAŁO |
| 300 | OK — 1 danie |
| 396 | OK — 1 danie |
| 400 | ZA DUŻO (1 danie + ostrzeżenie; 400/2=200 < 272) |
| 450 | ZA DUŻO (225 < 272) |
| 600 | OK — 2 dania (po 300) |
| 700 | OK — 2 dania (po 350) |

**Konsekwencja dla batcha mielonego:** kotlety + sos = **2 dania** → zakup celuje w `2 × przedział` (≈ 580–790 g: dwie tacki ~300–400 g albo jedno duże opakowanie). Pojedynczej tacki 250–400 g **nie** rozbijamy już na dwa dania — to uchyla notatki „½ tacki" / „reszta tacki". Reguła „gotuj oba dania tego samego dnia" (brak zamrażarki) zostaje.

**Rozdział pojęć (zapisz, żeby się nie mieszało):** przelicznik porcji `dorosły 1 / dziecko 0,5` dotyczy skali całego dania (`base_servings` — węglowodany, dodatki); mięso ma osobny profil przedziałowy powyżej.

## [DECISION] — dopisz do rejestru w README.md

- **[DECISION] Przedziały mięsa per danie.** Profil w preferences (dorosły 180–220 g; mnożnik 0,3–0,4× per dziecko, definiowalny); przedział dania liczony ze składu jedzących (obecnie ~290–400 g). Zastępuje sztywne nominały per mięso.
- **[DECISION] Klasyfikacja opakowania.** Największe n z W/n w przedziale → n dań; opakowania = 1 danie nie dzielimy (zasada Moniki); W < min → ostrzeżenie „może zabraknąć"; W > max bez podziału → „za dużo — dostosuj albo świadomie więcej (resztki → journal)".
- **[DECISION] Batch mielone = 2 dania zakupowo** (≈ 580–790 g łącznie); uchyla podział pojedynczej tacki pół na pół.
- **[DECISION] Demand mięsa: `qty` = środek przedziału łącznego (kg) + opcjonalne `qty_range: [min, max]`** — pole dodatkowe kontraktu (expenses ignoruje nieznane pola); klasyfikacja zakupu odbywa się po stronie meals przy raporcie „kupiłem X g".

## Operacje

1. **`preferences.md`** (Gospodarstwo): dodaj blok „Profil porcji mięsa" — dorosły 170–220 g; `Maja: 0,3–0,4×`, `Marceli: 0,2–0,3×` (z dopiskiem „definiowalne — dzieci rosną"); wyliczony przedział dania ~290–400 g dla obecnego składu; zasada Moniki (tacki w przedziale nie dzielimy); rozdział pojęć wobec przelicznika 0,5 (patrz wyżej).
2. **`ingredients.md`**: w regule mięsa paczkowanego zastąp nominały per mięso odwołaniem do profilu („przedział dania z preferences, obecnie ~290–400 g; klasyfikacja opakowań wg README"). W uwagach mięs usuń „1 danie ≈ …"; zostaw informacje o formie (sznycle 2–4 plastry itp.).
3. **`recipes/`**: w `kotlety-mielone` i `sos-pomidorowy-z-mielonym` anchor `qty: 1, unit: danie` z notą „wg przedziału dania (~290–400 g)"; usuń „½ tacki"/„reszta tacki"; w mielonych advance_prep: „sos tego samego dnia (brak zamrażarki); zakup na oba dania ≈ 2 × przedział". W `kebab-z-indyka` / `pulpeciki` noty w duchu „z opakowania wielodaniowego — podział wg klasyfikacji (np. 600 g = 2 dania)". `kotlety-schabowe`: nota anchor „opakowanie w przedziale — zużyj całe". `git grep -n "tacki"` i uporządkuj pozostałości.
4. **`CLAUDE.md`** (Zasady twarde): przedział dania z profilu + algorytm klasyfikacji (skrót) + obowiązek: gdy Marcin raportuje zakup mięsa („kupiłem X g"), sklasyfikuj i w razie potrzeby ostrzeż dokładnie w brzmieniu modelu; przy generacji listy zakupów podawaj przedział łączny per mięso (dania × przedział).
5. **Plany przyszłe**: demand mięsa `qty` = środek przedziału łącznego + `qty_range`; strona zakupowa renderuje „X dań (~min–max g łącznie, 1–2 opak.)"; linia mięsa w karcie dnia: „1 danie — całe opakowanie w przedziale ~290–400 g".
6. **`plans/2026-W31/`**: `demand[]` nie zmieniaj (kontrakt skonsumowany). Linie filetu śr/czw na stronie mogą brzmieć „½ opakowania 600 g (~300 g — w przedziale ✓)". **Zgłoś Marcinowi w podsumowaniu sesji:** plan pn/wt (kotlety + sos) to 2 dania mielonego, a zakup wg starego modelu mógł objąć 1 tackę — jeśli tak, rekomendacja dokupu ~300–400 g przed poniedziałkiem; po potwierdzeniu dokupu wystaw `revision: 2` z dodatkową pozycją (korekta przed wykonaniem = legalna rewizja).
7. **`kpi.md` / `journal.json`**: bez zmian schematu („świadomie więcej" ląduje w `leftovers`).

## Akceptacja — przed commitem

1. Funkcja klasyfikacji (choćby inline w skrypcie sprawdzającym) przechodzi wszystkie wektory testowe z tabeli.
2. `git grep -n "½ tacki\|reszta tacki\|1 danie ≈"` — pusto (poza `docs/migrations/`).
3. Przedział w preferences wylicza się do 272–396 g dla obecnego profilu (test arytmetyki, nie hardkodu).
4. JSON-y poprawne; brak regresji checków z migracji 01.

## Commit

`feat: przedziały mięsa per danie + klasyfikacja opakowań (profil w preferences) [DECISION x4]` — nie pushuj bez zielonej Akceptacji; podsumowanie sesji musi zawierać punkt o mielonym W31.
