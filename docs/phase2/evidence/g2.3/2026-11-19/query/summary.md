# Query diagnostics summary

## Q1 — order listing N+1

MySQL `general_log` was enabled only around each isolated API request, stored in the MySQL table, then disabled. SQL statements are preserved verbatim in `q1-order-listing.json`.

| Page content | Captured SELECTs | Order queries | `order_items` queries | API diagnostic latency |
|---:|---:|---:|---:|---:|
| 1 | 4 | 2 | 1 | 68.048 ms |
| 5 | 8 | 2 | 5 | 34.723 ms |
| 20 | 23 | 2 | 20 | 62.575 ms |
| 50 | 53 | 2 | 50 | 50.642 ms |

The stable non-item statements are the page SELECT, count SELECT, and a connection/version SELECT. One additional `order_items` SELECT occurred per mapped order. This is a runtime-observed N+1 pattern, not an inference from mapping alone: **CONFIRMED DEFECT / DB-07 confirmed**. A detail request used one order SELECT plus one item SELECT (and the stable version SELECT), so the growth defect is the list mapping.

## Q2 — food search

Synthetic levels were 100, 1,000 and 5,000 food rows, with 10% matches. `EXPLAIN ANALYZE` showed a primary-index scan visiting 100/1,000/5,000 rows for both keyword-only and category-filtered search. At 5,000 rows, filter execution was about 4.29–4.32 ms; single diagnostic API latency was 53.742 ms without category and 44.223 ms with category. The leading wildcard plus `LOWER()` did not use the unique name index. A foreign-key category index exists, but the optimizer chose the primary scan for this single-category synthetic distribution and `ORDER BY id`.

The access-plan fact is **confirmed**. End-user performance severity remains **INCONCLUSIVE / DB-06 risk retained** because the data is synthetic, cardinality is modest, the response returns 500 records, and G2.3 has no representative workload/SLO threshold.

## Q3 — order filter, pagination and sort

Synthetic total order levels were 100, 1,000 and 5,000 across 21 users; the measured customer owned 5, 48 and 239 orders. Plans used the implicit `fk_orders_user(user_id)` index, then filtered status/type and sorted `created_at DESC, id DESC`. There is no composite status/type/sort index. At total 5,000 rows the customer plan examined 239 owner rows, sorted them, and returned 20 in about 0.459 ms in `EXPLAIN ANALYZE`; the count plan also scanned 239 owner-index rows in about 0.311 ms. Offset 100 sorted/limited 120 of the 239 owner rows.

API list SQL count at the two larger levels was 23 SELECTs for 20 content rows, dominated by the same N+1 item loading. Diagnostic API latency was 22.091, 28.855 and 33.573 ms at the three levels; these are single measurements, not benchmark numbers.

Index and plan behavior are **confirmed**; a production bottleneck conclusion is **INCONCLUSIVE / DB-06 risk retained** because workload mix, SLO, warm-up/repetitions and representative cardinality are intentionally deferred to later benchmark work. No index was created or changed.

## Q4 — scaling controls

All synthetic rows were inserted only into the dedicated G2.3 database and removed after each investigation. Maximum business cardinality was 5,000 food rows or 5,000 orders plus one item per order. `ANALYZE TABLE` refreshed optimizer statistics; it did not alter schema or indexes. `general_log` was confirmed OFF at harness exit.
