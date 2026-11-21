# Concurrency verification summary

## Method

The harness used the real backend HTTP endpoints and the dedicated MySQL 8.4 database. Each scenario ran 15 independent rounds with concurrency level two. A `threading.Barrier` released both client workers together; HTTP start/end timestamps and DB state before/after each round are in the raw JSON.

Across all five scenarios, client request intervals overlapped in 15/15 rounds. Median request-start delta was 0 ms for C1/C2/C3/C5 and 0.628 ms for C4; maximum delta was 6.870 ms. This establishes near-simultaneous HTTP attempts, not an in-transaction database barrier. No artificial application hook, mock database, source edit, or retry-to-green was used.

## Reviewed results

| Scenario | Rounds | HTTP/data outcome | Reviewed classification |
|---|---:|---|---|
| C1 — same food checkout | 15 | 6 rounds returned 201+201 and committed 14 units from initial stock 10 while final stock was 3. Remaining 9 rounds committed one order and left loser cart intact. | **CONFIRMED DEFECT** — overselling and lost stock update in 6/15. |
| C2 — same cart checkout | 15 | Every round ended with exactly one order, quantity 2, stock 8 and empty cart. Loser outcomes: 11×409, 2×400 `EMPTY_CART`, 2×500 `INTERNAL_ERROR`. | **INCONCLUSIVE** — data invariants held, but loser semantics include two unhandled stale-row failures. |
| C3 — same order cancellation | 15 | Every round ended `CANCELLED`, stock restored exactly once from 8 to 10. 13 rounds returned 200+200; 2 returned 200+409. | **OBSERVED CORRECT** for final data invariants; no claim beyond these attempts. |
| C4 — admin stock set vs checkout | 15 | Both requests succeeded in every round. Final stock distribution: 7 in 12 rounds, 20 in 2, 17 in 1. | **CONFIRMED DEFECT** — final 7 is outside serial outcomes 17/20 and loses the successful absolute stock update. |
| C5 — first cart creation | 15 | Each round returned one 200 and one 409 `CONFLICT`; exactly one cart and one item with quantity 1 remained. | **OBSERVED CORRECT** in tested conflict semantics; unique constraint rollback preserved data. |

## Invariants and interpretation

- C1 initial stock was 10; each of two customers requested 7. Six rounds committed two orders totaling 14 while persisting stock 3, proving both overselling and a lost update. There were no partial orders and both successful carts were cleared.
- C2 expected at most one order and stock `10 - committed quantity`. All rounds met this. The two HTTP 500 rounds are preserved, not hidden: backend log identifies `ObjectOptimisticLockingFailureException` / `StaleObjectStateException` while deleting the same `CartItem`; this exception fell through to the generic 500 handler.
- C3 restored stock once even when both stale transactions returned 200. Because API idempotency/loser-response policy is not explicitly defined, the classification is limited to data correctness.
- C4 contract is sufficiently specific for this check: `FoodService.updateFood` assigns the request's non-null `stockQuantity` (20), and checkout subtracts 3. A serial execution must end at 17 (update then checkout) or 20 (checkout then update). Final 7 with both HTTP calls successful is a reproducible non-serializable/lost-update outcome.
- C5's `uq_carts_user` constraint rejected one creator with 409 in all rounds; no cart/item was lost after rollback.

The executed harness emitted a deliberately conservative `INCONCLUSIVE` label for C4 in its raw summary. This review upgrades C4 to **CONFIRMED DEFECT** based on the recorded absolute-update contract and the 12 non-serializable final states; raw output remains unchanged for auditability.
