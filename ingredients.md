# Słownik składników — `ingredients.md`

Kanoniczne nazwy składników = odpowiednik klas W3 po stronie `meals`.

**Reguły (z kontraktu, sekcja 5.2 EXTRACT):**
- Każdy przepis i `demand.json` referencuje **wyłącznie** nazwy z tego słownika.
- Nowy składnik = najpierw wpis tutaj, dopiero potem użycie w przepisie.
- `ean_hint` uzupełniamy TYLKO przy lojalności marki (typ A); domyślnie składnik idzie klasą (typ B).
- Jednostka bazowa = jednostka używana w `demand.json` (kg / l / szt).

## Mięso i ryby

| Nazwa kanoniczna | Jedn. | Aliasy | Uwagi |
|---|---|---|---|
| schab wieprzowy | kg | schab | plastry na kotlety |
| łopatka mielona wieprzowa | kg | mielone wieprzowe | tacka = 400 g (brak zamrażarki: planować zużycie całej tacki) |
| filet z piersi indyka | kg | pierś indyka | typowy filet ~260 g |
| łosoś świeży | kg | filet z łososia | filet; sprawdzić ości przed pieczeniem |

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
