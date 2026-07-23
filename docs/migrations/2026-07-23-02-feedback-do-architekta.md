# Feedback do architekta — migracja 02 (przedziały mięsa)

Migracja wykonana, Akceptacja zielona (wektory klasyfikacji, przedział 272–396, grep czysty, JSON-y, `--check`). Dwa rozjazdy dokumentu vs. stan repo/rodziny — do rewizji migracji na przyszłość.

## #3 — założenie „brak zamrażarki" jest nieaktualne

**Dokument:** batch mielonego opiera się na „brak zamrażarki" (kotlety + sos tego samego dnia) i re-łączy sos z kotletami (advance_prep, notatki, `preferences.md`).

**Stan faktyczny (potwierdzone przez Marcina):** zamrażarka **jest**. Dodatkowo Marcin już wcześniej prosił wprost o rozprzężenie sosu („jak trzeba to robię, ale nie zawsze muszę") — migracja to cofała.

**Skutek dla modelu (zastosowane w tej sesji):**
- „Batch = 2 dania zakupowo" **zostaje** (kupujemy mielone na 2 dania), ale **rozkład w czasie jest swobodny**: kotlety dziś, drugą porcję (surową albo jako ugotowany sos) mrozimy.
- **Sos = osobne, opcjonalne danie** (`składnik-bazowy` robiony, gdy potrzebny), nie wymuszony tego samego dnia.
- Plan W30 rozprzężony: kotlety (Pt) → druga porcja do zamrażarki → sos (Pn, osobno) → 2× makaron.

**Rekomendacja do dokumentu:** usunąć regułę „brak zamrażarki → oba dania tego samego dnia"; w advance_prep mielonego zostawić wyłącznie notę zakupową (2 dania) + opcję mrożenia; w `preferences.md` „zamrażarka: jest". Reguła zakupowa i przedziały bez zmian.

## #4 — twarde odwołanie do `plans/2026-W31`

**Dokument:** adresuje `plans/2026-W31` i zakłada, że jego `demand[]` jest już **skonsumowany** (nie ruszać), a jedynie linie na stronie doprecyzować.

**Stan faktyczny:** repo przeszło na **ścisłe ISO** — bieżący plan to `2026-W30` (24.07 to ISO W30; wcześniejsze „W31" było błędną etykietą, skorygowaną osobno). Plan bieżący **nie był skonsumowany** przez expenses, więc `demand[]` przeliczyłem pod nowy model (legalna rewizja przed wykonaniem, `revision:` w górę).

**Rekomendacja do dokumentu:** migracje niech odwołują się do „bieżącego planu / id ISO", nie do zahardkodowanego numeru tygodnia; nie zakładać z góry, że `demand[]` danego planu jest już wysłany — sprawdzać stan (kontrakt konsumowany vs. plan przyszły).

## P.S. — drobna niespójność wewnętrzna migracji (#2)

Operacje krok 1 podają `Marceli: 0,2–0,3×`, ale [DECISION], przykład i Akceptacja #3 wymagają **272–396 g**, co wychodzi tylko przy obu dzieciach `0,3–0,4×` (a także `dorosły 170–220`, nie `180–220` z jednego z [DECISION]). Ustawiłem `0,3–0,4×` pod Akceptację, z dopiskiem „do potwierdzenia" w `preferences.md`. Warto ujednolicić liczby w dokumencie.
