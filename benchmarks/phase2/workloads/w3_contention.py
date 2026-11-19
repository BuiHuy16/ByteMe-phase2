#!/usr/bin/env python3
"""Barrier-based correctness workload. Keep separate from throughput percentiles."""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import pathlib
import subprocess
import threading
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[3]
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def compose(args) -> list[str]:
    return ["docker", "compose", "--env-file", args.env_file, "-p", args.project,
            "-f", "compose.yaml", "-f", "benchmarks/phase2/compose.benchmark.yaml"]


def mysql(args, sql: str) -> str:
    shell = 'MYSQL_PWD="$MYSQL_PASSWORD" mysql --batch --raw --skip-column-names -u"$MYSQL_USER" "$MYSQL_DATABASE"'
    proc = subprocess.run(compose(args) + ["exec", "-T", "mysql", "sh", "-lc", shell], cwd=ROOT,
                          input=sql, text=True, encoding="utf-8", capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def api(args, method: str, path: str, token: str, payload=None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Accept": "application/json", "Authorization": "Bearer " + token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(args.base_url + path, data=data, headers=headers, method=method)
    started = now()
    start_ns = time.perf_counter_ns()
    try:
        with HTTP.open(request, timeout=30) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    body = json.loads(raw.decode()) if raw else None
    compact = None
    if isinstance(body, dict):
        compact = {key: body.get(key) for key in ("id", "code", "status", "message") if key in body}
    return {"started_at_utc": started, "ended_at_utc": now(),
            "elapsed_ms": round((time.perf_counter_ns() - start_ns) / 1_000_000, 3),
            "http_status": status, "body": compact}


def parallel_requests(args, requests: list[dict]) -> list[dict]:
    barrier = threading.Barrier(len(requests) + 1)

    def worker(index: int, request: dict):
        barrier.wait(timeout=10)
        result = api(args, **request)
        result["actor_index"] = index
        return result

    with futures.ThreadPoolExecutor(max_workers=len(requests)) as pool:
        pending = [pool.submit(worker, i + 1, request) for i, request in enumerate(requests)]
        barrier.wait(timeout=10)
        return [future.result(timeout=45) for future in pending]


def clean(args, users: list[int], food_id: int, stock: int) -> None:
    ids = ",".join(map(str, users))
    mysql(args, f"""
        DELETE oi FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id IN ({ids});
        DELETE FROM orders WHERE user_id IN ({ids});
        DELETE ci FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id IN ({ids});
        DELETE FROM carts WHERE user_id IN ({ids});
        UPDATE foods SET stock_quantity={stock} WHERE id={food_id};
    """)


def add(args, actor: dict, food_id: int, quantity: int) -> dict:
    return api(args, "POST", "/api/cart/items", actor["token"], {"foodId": food_id, "quantity": quantity})


def checkout(actor: dict) -> dict:
    return {"method": "POST", "path": "/api/orders", "token": actor["token"],
            "payload": {"orderType": "DINE_IN", "tableNumber": "W3", "recipientName": None,
                        "shippingPhone": None, "shippingAddress": None,
                        "paymentMethod": "CASH", "note": "benchmark-w3"}}


def state(args, users: list[int], food_id: int) -> dict:
    ids = ",".join(map(str, users))
    values = mysql(args, f"""
        SELECT COUNT(*) FROM orders WHERE user_id IN ({ids});
        SELECT COALESCE(SUM(oi.quantity),0) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id IN ({ids}) AND oi.food_id={food_id};
        SELECT stock_quantity FROM foods WHERE id={food_id};
        SELECT COUNT(*) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id IN ({ids});
    """).splitlines()
    return dict(zip(("orders", "committed_quantity", "stock", "cart_items"), map(int, values)))


def run_c1(args, actors, food, initial, round_id):
    users = [a["id"] for a in actors]
    clean(args, users, food["id"], initial)
    for actor in actors:
        if add(args, actor, food["id"], 7)["http_status"] != 200:
            raise RuntimeError("C1 fixture failed")
    before = state(args, users, food["id"])
    responses = parallel_requests(args, [checkout(a) for a in actors])
    after = state(args, users, food["id"])
    violations = []
    if after["committed_quantity"] > initial:
        violations.append("OVERSELLING")
    if after["stock"] != initial - after["committed_quantity"]:
        violations.append("LOST_UPDATE")
    return {"round": round_id, "before": before, "responses": responses, "after": after, "violations": violations}


def run_c2(args, actor, food, initial, round_id):
    clean(args, [actor["id"]], food["id"], initial)
    if add(args, actor, food["id"], 2)["http_status"] != 200:
        raise RuntimeError("C2 fixture failed")
    before = state(args, [actor["id"]], food["id"])
    request = checkout(actor)
    responses = parallel_requests(args, [request, request])
    after = state(args, [actor["id"]], food["id"])
    violations = []
    if after["orders"] > 1 or after["committed_quantity"] > 2:
        violations.append("DOUBLE_CHECKOUT")
    if after["stock"] != initial - after["committed_quantity"]:
        violations.append("STOCK_MISMATCH")
    return {"round": round_id, "before": before, "responses": responses, "after": after, "violations": violations}


def run_c4(args, admin, actor, food, initial, round_id):
    clean(args, [actor["id"]], food["id"], initial)
    if add(args, actor, food["id"], 3)["http_status"] != 200:
        raise RuntimeError("C4 fixture failed")
    before = state(args, [actor["id"]], food["id"])
    update = {"categoryId": food["category_id"], "name": food["name"],
              "description": food["description"], "price": food["price"], "imageUrl": None,
              "stockQuantity": 20, "status": food["status"]}
    responses = parallel_requests(args, [checkout(actor), {"method": "PUT", "path": f"/api/foods/{food['id']}",
                                                    "token": admin["token"], "payload": update}])
    after = state(args, [actor["id"]], food["id"])
    valid = [17, 20] if responses[0]["http_status"] == 201 else [20]
    violations = [] if after["stock"] in valid else ["NON_SERIALIZABLE_FINAL_STOCK"]
    return {"round": round_id, "before": before, "responses": responses, "after": after,
            "serial_final_stock": valid, "violations": violations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--actors", required=True)
    parser.add_argument("--rounds", type=int, default=15)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not (args.project.startswith("byteme-g24-") or args.project.startswith("byteme-benchmark-")):
        raise SystemExit("Refusing non-benchmark project")
    fixture = json.loads(pathlib.Path(args.actors).read_text(encoding="utf-8"))
    by_label = {actor["label"]: actor for actor in fixture["contention"]}
    food = fixture["shared_food"]
    initial = food["initial_stock"]
    results = {"started_at_utc": now(), "rounds_per_scenario": args.rounds, "scenarios": {}}
    specs = {
        "same_food_checkout": lambda n: run_c1(args, [by_label["c1a"], by_label["c1b"]], food, initial, n),
        "same_cart_checkout": lambda n: run_c2(args, by_label["c2"], food, initial, n),
        "admin_stock_vs_checkout": lambda n: run_c4(args, fixture["admin"], by_label["c4"], food, initial, n),
    }
    try:
        for name, function in specs.items():
            rounds = [function(i) for i in range(1, args.rounds + 1)]
            results["scenarios"][name] = {
                "rounds": rounds,
                "violation_rounds": [r["round"] for r in rounds if r["violations"]],
                "server_error_rounds": [r["round"] for r in rounds
                                        if any((x["http_status"] or 0) >= 500 for x in r["responses"])],
            }
    finally:
        clean(args, [a["id"] for a in fixture["contention"]], food["id"], initial)
    results["finished_at_utc"] = now()
    results["method_limit"] = "Client barrier does not prove a database in-transaction barrier."
    pathlib.Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({name: {"violations": data["violation_rounds"], "server_errors": data["server_error_rounds"]}
                      for name, data in results["scenarios"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
