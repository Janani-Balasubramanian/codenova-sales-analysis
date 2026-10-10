# Data dictionary and provenance

## Dataset contract

Entirely synthetic, generated locally with NumPy seed `20261010`. No real customers or proprietary records. Study period: 1 January 2024 to 31 December 2025. Geography: fictional allocations among four broad Indian regions. Currency: INR, with 100 paise per INR.

One row is one completed order containing a single product type and one or more units. Multi-product baskets, cancelled orders, refunds, taxes, shipping and overhead are not modeled. The catalog has 12 products in four categories. Catalog prices and costs are fixed throughout the study, which makes deterministic reference recovery defensible for this fixture only.

The generator creates 3,177 base orders, then injects 30 equivalent duplicates and eight conflicting versions for 3,215 raw rows. Quantities are sampled from 1, 2, 3, 4 and 18 units. Q4 volume is deliberately 55% higher before rounding, 2025 base counts are 12% higher, and regional sampling favors South. The deliberate data defects are concentrated in early rows; this limits inference from trends after cleaning.

## Raw and clean business fields

| Field | Clean type | Definition and rule |
| --- | --- | --- |
| `order_id` | string | `ORD` followed by six digits; unique among retained orders |
| `order_date` | ISO date | Valid date in 2024-2025; raw input supports YYYY-MM-DD or DD/MM/YYYY |
| `product_id` | string | Foreign key into the supplied catalog, P01-P12 |
| `category` | string | Electronics, Home, Fashion or Stationery; verified using catalog |
| `region` | string | North, South, East, West or explicit `Unspecified` |
| `quantity` | integer | Strictly positive units; no arbitrary upper cap |
| `unit_price` | decimal string | INR per unit, before discount; parsed to exact integer paise for analysis |
| `unit_cost` | decimal string | INR cost of goods per unit; excludes overhead |
| `discount_pct` | integer | Order percentage discount, inclusive range 0-100 |

Raw fields are read as strings to preserve errors and leading/trailing spaces for auditing. Blank/whitespace-only values count as missing. Clean CSV types are enforced by the consuming scripts, since CSV itself has no schema.

## Additional output fields

| Field | Meaning |
| --- | --- |
| `source_row` | Original CSV line number; line 1 is the header |
| `quantity_outlier` | True if quantity lies outside its category's Q1 - 1.5*IQR or Q3 + 1.5*IQR fence; retained |

## Catalog fields

`product_id`, `category`, `product_name`, `unit_price_paise`, `unit_cost_paise`. Paise columns are nonnegative integer values. The catalog is synthetic reference data, not a scraped price list.

## Derived sales measures

| Measure | Definition |
| --- | --- |
| `gross_paise` | quantity x unit_price_paise |
| `discount_paise` | round-half-up(gross_paise x discount_pct / 100), per order |
| `net_paise` | gross_paise - discount_paise |
| `cost_paise` | quantity x unit_cost_paise |
| `profit_paise` | net_paise - cost_paise; gross profit, not net profit |
| `margin_pct` | 100 x sum(profit_paise) / sum(net_paise) |
| `aov_inr` | sum(net_paise) / 100 / distinct order count |
| `units` | sum(quantity) |

Season buckets: December-February winter, March-May pre-monsoon, June-September monsoon, October-November post-monsoon. Compare revenue per observed month to correct for unequal bucket lengths. These are calendar labels rather than regional climate observations.

## Lineage and integrity

Raw SHA-256: `100c1f522bdc754a79d314639f8633c3e3ef05b93ed1f155fdb590506b0bc60c`.

Clean SHA-256: `3496b1f75261f24ab1e302fb80b297f02ff89bfa7647a9456df515844a04c3ca`.

The cleaning manifest verifies source preservation. Both project folders contain identical clean data. If generating on an environment with different newline conventions, raw byte hashes can differ even when tabular content is equivalent; use the included fixtures for exact byte reproduction.

## Reuse

The data was generated for this educational project; no third-party dataset license is involved. Third-party Python dependencies retain their own licenses. Do not describe the synthetic rows as real company sales.
