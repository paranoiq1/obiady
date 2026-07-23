# Słownik składników — `ingredients.md`

Kanoniczne nazwy składników = odpowiednik klas W3 po stronie `meals`.

**Reguły (z kontraktu, sekcja 5.2 EXTRACT):**
- Każdy przepis i `demand.json` referencuje **wyłącznie** nazwy z tego słownika.
- Nowy składnik = najpierw wpis tutaj, dopiero potem użycie w przepisie.
- `ean_hint` uzupełniamy TYLKO przy lojalności marki (typ A); domyślnie składnik idzie klasą (typ B).
- Jednostka bazowa = jednostka używana w `demand.json` (kg / l / szt).

## Mięso i ryby

Mięso „daniowe" w kartach zapisujemy jako `unit: danie` (nie w gramach). Gramaturę liczy `build.py` z **przedziału dania** (profil w `preferences.md`, obecnie **272–396 g**) i klasyfikuje opakowanie przy zakupie (algorytm w `README.md`). Łosoś — na wagę, poza modelem.

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| schab wieprzowy | kg | schab | mięso daniowe (przedział + klasyfikacja); sznycle na kotlety |
| łopatka mielona wieprzowa | kg | mielone wieprzowe | mięso daniowe (przedział dania z preferences, ob. ~290–400 g; klasyfikacja wg README); mielone = 2 dania (kotlety + sos), 2. porcję można zamrozić |
| filet z piersi indyka | kg | pierś indyka | mięso daniowe; opakowanie wielodaniowe dzielone wg klasyfikacji |
| łosoś świeży | kg | filet z łososia | na wagę (poza modelem daniowym); sprawdzić ości przed pieczeniem |

## Nabiał i jajka

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| jajka | szt | jajko | |
| jogurt naturalny gęsty | kg | jogurt typu greckiego | marynaty i sosy |
| masło | kg | | spiżarnia bazowa |

## Warzywa i owoce

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| cebula | szt | | |
| czosnek | szt | główka czosnku | jedn. = główka; w przepisach ząbki |
| marchew | szt | marchewka | |
| brokuł | szt | | |
| cukinia | szt | | preferowana mała |
| ogórek | szt | ogórek zielony | |
| cytryna | szt | | |
| fasolka szparagowa | kg | | |

## Suche i słoiki

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| kasza gryczana | kg | | torebki 4 × 100 g |
| ryż basmati | kg | | |
| makaron fusilli | kg | fusilli | |
| kuskus perłowy | kg | | op. ~400 g |
| bułka tarta | kg | | op. ~500 g |
| passata pomidorowa | kg | passata | butelka 680 g |
| ciecierzyca konserwowa | szt | ciecierzyca z puszki | puszka 400 g (~240 g po odsączeniu) |
| groszek zielony konserwowy | szt | groszek z puszki | mała puszka |

## Spiżarnia bazowa (przyprawy i tłuszcze)

Nie trafiają do `demand.json` per plan — dokupowane, gdy się kończą.

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| olej | l | olej do smażenia | do doprecyzowania klasy (rzepakowy?) przy matchingu w `expenses` |
| oliwa z oliwek | l | oliwa | |
| sól | kg | | |
| pieprz czarny mielony | kg | pieprz | |
| papryka słodka mielona | kg | słodka papryka | |
| kumin mielony | kg | kmin rzymski | |
| oregano suszone | kg | oregano | |

## Konwersje jednostek (blok maszynowy)

Sekcje z tabelami powyżej są źródłem prawdy dla nazw kanonicznych, jednostek bazowych i przynależności do spiżarni (nagłówek „Spiżarnia bazowa"). Poniższy blok YAML dokłada to, czego tabela nie wyraża: przeliczniki jednostek kuchennych na bazowe (`build.py` normalizuje nimi ilości z kart) oraz etykiety opakowań na liście zakupów. Nowa jednostka w karcie → najpierw wpis tutaj.

```yaml
units:
  # jednostka źródłowa → mnożnik do jednostki bazowej składnika (kg / l / szt)
  base:
    g: 0.001        # → kg
    ml: 0.001       # → kg lub l (gęstość ≈ 1; przybliżenie do zakupów, np. passata)
    kg: 1
    l: 1
    szt: 1
  # jednostki kuchenne swoiste dla składnika (gdy nie da się globalnie)
  per_ingredient:
    czosnek:
      ząbek: 0.25            # 1 główka = 4 ząbki
    jogurt naturalny gęsty:
      łyżka: 0.025           # 1 łyżka ≈ 25 g
    bułka tarta:
      łyżka: 0.011           # 1 łyżka ≈ 11 g
# etykieta opakowania na liście zakupów dla składników liczonych w szt
pack_label:
  czosnek: główka
  ciecierzyca konserwowa: puszka
  groszek zielony konserwowy: mała puszka
```
