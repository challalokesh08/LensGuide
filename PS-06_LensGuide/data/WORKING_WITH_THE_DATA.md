# Working with the data — PS-06

Everything in this folder is yours to use. It is fully synthetic: no real people, no personal
data, nothing scraped. It is safe to commit to a public repository.

**12,289 rows across 13 tables**, of which 12 are the tables your
statement is actually built on. The rest are small reference tables the others point at.

## Ninety seconds to your first query

```bash
sqlite3 data/PS-06.db < data/queries/starter_queries.sql
```

Or open `data/PS-06.db` in any SQLite client. Nothing to install, nothing to import.

## Into Postgres, if you would rather build properly

```bash
createdb travel
psql -d travel -f data/schema.sql
for f in data/csv/*.csv; do
  t=$(basename "$f" .csv | sed 's/^[0-9]*_//')
  psql -d travel -c "\copy $t FROM '$f' CSV HEADER"
done
```

The CSV filenames are numbered in load order, so foreign keys resolve as you go.

## The eight rules

These apply to the fields that came with the data. Anything you add yourself is entirely your
own business.

| # | Rule |
|---|---|
| R1 | **Additive only.** Add columns, tables and stores freely. Never rename, drop or repurpose a field that came with the data. If you need different semantics, add a new field beside it. |
| R2 | **IDs are opaque prefixed strings** — `htl_a91f3c`, `usr_0f22b1`. Never integers, never parsed for meaning, never re-issued. |
| R3 | **Money is a pair**: a fixed-point decimal with exactly 2 places, plus an ISO-4217 currency code. Never a float. |
| R4 | **Time is ISO-8601 with an offset.** Instant fields end `_at` and carry an offset; calendar dates end `_date` and have no zone. |
| R5 | **Enums are lowercase snake_case**, and the legal values are in `data/enums.json`. |
| R6 | **Language is a BCP-47 tag** — `ta`, `hi`, `en-IN`. Never "Tamil". |
| R7 | **Geography is WGS-84** decimal degrees to 6 places. A row has both `lat` and `lng`, or neither. |
| R8 | **Nothing is hard-deleted.** Mutable rows carry `status` and `updated_at`; cancellations and removals stay visible. |

They exist so that sixteen independent builds can be put together afterwards without a rewrite.

## Money, in full — the one that costs people an hour

The danger is not the storage type. It is the moment a value passes through a float on its way
somewhere, and a naive CSV parser does exactly that.

```python
# Python
from decimal import Decimal
rate = Decimal(row["base_rate"])          # never float(...)
```
```python
# pandas — keep money columns as text, then convert
df = pd.read_csv(p, dtype={"base_rate": str, "currency": str})
df["base_rate"] = df["base_rate"].map(Decimal)
```
```javascript
// JavaScript — a JSON number is an IEEE-754 double. Use a decimal library.
import Decimal from "decimal.js";
const rate = new Decimal(row.base_rate);  // row.base_rate is a STRING on purpose
```
```java
// Java / Kotlin
BigDecimal rate = new BigDecimal(row.get("base_rate"));
```

In `PS-06.db` the money columns are declared `TEXT`. That is deliberate: SQLite's NUMERIC
affinity would turn `8500.00` into the float `8500.0` and the exact value would be gone. Cast
to a number only for sorting, never for arithmetic you will show someone.

Splitting money between people uses **largest-remainder** allocation so the parts sum exactly to
the whole: ₹1000.00 three ways is `333.34 + 333.33 + 333.33`, never three times `333.33`.

## Non-money decimals in SQLite read back as floats

Money columns are `TEXT` in the `.db`, so they come back exactly. Other decimals — `carbon_kg`,
`distance_km`, `reference_carbon_kg`, rates and percentages — carry SQLite's REAL affinity, so
`SELECT` hands you a float. `11.985` is still `11.985` when you print it, but do not compare two
of them with `==` after arithmetic. Either compare with a small tolerance, wrap the value as
`Decimal(str(v))` before comparing, or read those columns from the CSVs, where they are exact
text. This bites hardest when you are checking one of the reconstructible totals listed above.

## Currencies with 0 or 3 decimal places

JPY and KRW have no minor unit; KWD and BHD have three. They are still stored as 2-place
decimals with trailing zeros. The true exponent is in `currencies.minor_unit_exponent` and is
for display only.

## What is derived, and what is not

Some columns are totals or ground truth that you can rebuild from other tables. Where that is
true it is true exactly — if you reconstruct one of these and get a different number, it is a
defect and we want to hear about it.

| Column | Rebuild it from |
|---|---|
| `itineraries.total_cost` / `total_duration_minutes` / `total_carbon_kg` | the sum over that itinerary's non-removed `itinerary_items` |
| `bookings.total_amount` | `sum(booking_items.line_total)` + `tax_amount`; each `line_total` is `unit_price x units` |
| `expense_splits.amount` | sums exactly to `expenses.amount`, largest-remainder |
| `receipts.total_amount_truth` | the sum of `line_items_truth` |
| `poi_travel_matrix.distance_km` / `bearing_deg` | the haversine and bearing between the two POIs' coordinates |
| `transfers.duration_minutes` | `distance_km` at the mode's constant speed — train 60, cab 42, bus 30, auto 27, ferry 21 km/h |
| `ar_wayfinding_cases.expected_bearing_deg` / `expected_distance_m` | the origin coordinates to the target POI |
| `xr_scenes.total_bytes` | the sum of that scene's `xr_scene_assets.bytes` |
| `eval_optimizer_cases.reference_*` | walk `reference_sequence`: POI `entry_cost` / `typical_duration_minutes` / `carbon_kg`, plus one `poi_travel_matrix` leg per consecutive pair, cheapest allowed mode, ties on fewer minutes |
| `eval_relevance_labels.grade` | how many of the query's `filters_json` constraints the entity misses — 0 misses is grade 3, 1 is grade 2, 2 is grade 1, wrong city is grade 0. About 12% of rows carry deliberate labeller noise, but a grade 3 always genuinely matches |

And three that look derived but are **not**, so do not try to reconcile them:

- **`hotels.guest_score`** is a platform aggregate over more reviews than the 25 you can see. It
  correlates with the mean of `hotel_reviews.rating` (r is about +0.67) but is not computed from
  it. Rank on whichever you can justify; just do not expect them to agree row by row.
- **`activities_poi.value_score`** is an editorial rating, not a function of price, popularity or
  duration.
- **`pricing_events`** is thirteen months of history; **`price_bounds`** are today's guardrails.
  About 4.5% of historical quotes sit outside today's floor and ceiling, which is what happens
  when guardrails are introduced after the fact. Respect the bounds going forward; do not treat
  the old rows as violations to fix.

## Checking your work

```bash
python3 tools/validate_conformance.py data/PS-06.db     # or point it at your own export
```

Standard library only, no install. It checks the mandatory core: IDs carry their prefixes, enum
values are legal, money is a 2-place decimal paired with a currency, timestamps carry offsets,
and foreign keys resolve. It prints PASS or FAIL. Run it in your first week rather than the hour
before you submit.

## If something in the data looks wrong

Ask on the data channel named in the email that sent you this folder — not in a DM and not in
your college group. If it is a real problem we would rather know early, and the answer goes to
everyone at once.
