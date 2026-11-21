# Database Initialization Summary

- Fresh project volume had seven expected tables and MySQL version `8.4.13`.
- Primary, unique, foreign-key and user CHECK constraints are listed in `schema-and-constraints.txt`.
- Before seed: every business table contained 0 rows; `stock_total=0`.
- Seed command ran exactly once, exit `0`.

| Table/metric | After seed |
|---|---:|
| users | 8 |
| categories | 6 |
| foods | 18 |
| carts | 5 |
| cart_items | 6 |
| orders | 8 |
| order_items | 16 |
| stock_total | 846 |

Sample grouping confirmed expected roles/statuses, 17 ACTIVE + 1 INACTIVE food, and the six order statuses represented by seed data.

