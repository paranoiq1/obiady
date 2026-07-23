# Preferencje rodziny — `preferences.md`

> **Status: SZKIC.** Do uzupełnienia w wywiadzie preferencji (pierwsza sesja projektu „Obiady", wzorzec AW).

## Gospodarstwo

- Przelicznik porcji (dodatki / węglowodany): **dorosły = 1, dziecko = 0,5**; skład Marcin (1) + Maja (0,5) + Marceli (0,5) = **2 porcje** (`base_servings`). Dotyczy SKALI dodatków — **mięso ma osobny profil przedziałowy** (niżej), nie ten przelicznik.
- **Jedna wersja dania dla wszystkich** — bez specjalnych wariantów per osoba.
- **Zamrażarka: jest — W NAPRAWIE, mrożenie niedostępne do odwołania.** (Gospodarstwo ma zamrażarkę — trwale uchyla „brak zamrażarki" z kickoffu; obecny status: w naprawie.) Póki niedostępna: nie planujemy mrożenia, nadwyżki → lodówka + `leftovers` w journalu, a mielone na 2 dania gotujemy tego samego dnia (reguła warunkowa). Po naprawie Marcin zmienia tę jedną linię — bez migracji.
- **Sos** to osobne, opcjonalne danie (robione, gdy potrzebne); w lodówce 3–4 dni.

## Profil porcji mięsa

Źródło **przedziału dania** dla mięsa (build.py liczy z profilu — nie hardkod). Mięso objęte daniami klasyfikujemy przy zakupie (algorytm w `README.md` / `CLAUDE.md`). **Łosoś kupujemy na wagę — poza tym modelem.**

**Zasada Moniki:** opakowania mieszczącego się „mniej więcej w porcji" (sklasyfikowanego jako **1 danie**) nie dzielimy na pół.

Bieżący przedział dania dla składu Marcin + Maja + Marceli wychodzi **272–396 g** (prezentacyjnie ~290–400 g). Zmiana składu (np. Monika przy stole) albo mnożników → przelicza się z profilu, nie jest zahardkodowany.

```yaml
meat_profile:
  adult_g: [170, 220]          # g mięsa na danie na dorosłego — ZATWIERDZONE (Marcin, PR#2); nadpisuje 180–220 z migracji 02
  adults: 1                    # dorośli przy stole (Monika przy stole → 2, przedział się przelicza)
  children:                    # mnożnik przedziału per dziecko — DEFINIOWALNE (dzieci rosną, aktualizować)
    Maja:    [0.3, 0.4]
    Marceli: [0.3, 0.4]        # składa się na zatwierdzony przedział 272–396 (Marceli §4 → EXTRACT rev 2)
```

## Marcin

- Lubi: _(wywiad)_
- Nie lubi: _(wywiad)_
- Ulubione potrawy: _(wywiad)_

## Monika

- Udział w obiadach: _(wywiad)_
- Lubi: _(wywiad)_
- Nie lubi: _(wywiad)_
- Ulubione potrawy: _(wywiad)_

## Maja

- Lubi: _(wywiad)_
- Nie lubi: _(wywiad)_
- Ulubione potrawy: _(wywiad)_

## Marceli

- Lubi: _(wywiad)_
- Nie lubi: _(wywiad)_

## Wspólne

- Linki do przepisów, z których korzystamy: _(wywiad)_
- Produkty zakazane / ograniczone w domu: _(wywiad)_
