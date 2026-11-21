#!/usr/bin/env python3
"""G2.3 black-box concurrency harness. Uses only HTTP and the isolated MySQL container."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import pathlib
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid


PASSWORD = os.environ["G23_ACTOR_PASSWORD"]
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "byteme-g23")
BASE_URL = os.environ.get("BYTEME_BASE_URL", "http://127.0.0.1:18081")
COMPOSE_FILE = os.environ.get("G23_COMPOSE_FILE", "compose.yaml")
OVERRIDE_FILE = os.environ.get("G23_OVERRIDE_FILE", ".local/g2.3/compose.override.yaml")
ENV_FILE = os.environ.get("G23_ENV_FILE", ".local/g2.3/runtime.env")
HTTP_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def compose_prefix() -> list[str]:
    return [
        "docker", "compose", "--env-file", ENV_FILE, "-p", PROJECT,
        "-f", COMPOSE_FILE, "-f", OVERRIDE_FILE,
    ]


def mysql(sql: str, *, root: bool = False) -> str:
    if root:
        shell = 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --batch --raw --skip-column-names -uroot "$MYSQL_DATABASE"'
    else:
        shell = 'MYSQL_PWD="$MYSQL_PASSWORD" mysql --batch --raw --skip-column-names -u"$MYSQL_USER" "$MYSQL_DATABASE"'
    proc = subprocess.run(
        compose_prefix() + ["exec", "-T", "mysql", "sh", "-lc", shell],
        input=sql, text=True, encoding="utf-8", capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mysql exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def scalar(sql: str, *, root: bool = False) -> str:
    rows = mysql(sql, root=root).splitlines()
    return rows[-1] if rows else ""


def api(method: str, path: str, *, token: str | None = None, payload=None, timeout: int = 30) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    started = utc_now()
    start_ns = time.perf_counter_ns()
    status = None
    raw = b""
    error = None
    try:
        with HTTP_OPENER.open(req, timeout=timeout) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    except Exception as exc:  # transport outcome is evidence, not hidden
        error = f"{type(exc).__name__}: {exc}"
    ended = utc_now()
    elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 3)
    body = None
    if raw:
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = raw.decode("utf-8", errors="replace")[:1000]
    return {
        "started_at_utc": started,
        "ended_at_utc": ended,
        "elapsed_ms": elapsed_ms,
        "http_status": status,
        "error": error,
        "body": body,
    }


def compact_response(response: dict) -> dict:
    body = response.get("body")
    summary = None
    if isinstance(body, dict):
        summary = {key: body.get(key) for key in ("id", "code", "status", "message") if key in body}
        if "items" in body and isinstance(body["items"], list):
            summary["item_count"] = len(body["items"])
    elif body is not None:
        summary = str(body)[:300]
    result = dict(response)
    result["body"] = summary
    return result


def concurrent_requests(specs: list[dict]) -> list[dict]:
    barrier = threading.Barrier(len(specs) + 1)

    def worker(index: int, spec: dict) -> dict:
        ready_at = utc_now()
        barrier.wait(timeout=10)
        released_at = utc_now()
        response = api(**spec)
        response.update({"actor_index": index, "barrier_ready_at_utc": ready_at,
                         "barrier_released_at_utc": released_at})
        return compact_response(response)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futures = [pool.submit(worker, i + 1, spec) for i, spec in enumerate(specs)]
        barrier.wait(timeout=10)
        return [future.result(timeout=45) for future in futures]


def register_actor(label: str, role: str = "CUSTOMER") -> dict:
    nonce = uuid.uuid4().hex[:10]
    email = f"g23.{label}.{nonce}@example.test"
    phone = "08" + str(int(nonce[:8], 16)).zfill(8)[-8:]
    payload = {"fullName": f"G23 {label}", "email": email, "phone": phone,
               "password": PASSWORD, "confirmPassword": PASSWORD}
    response = api("POST", "/api/auth/register", payload=payload)
    if response["http_status"] != 201:
        raise RuntimeError(f"register {label} failed: {compact_response(response)}")
    user_id = int(scalar(f"SELECT id FROM users WHERE email='{email}';"))
    if role != "CUSTOMER":
        mysql(f"UPDATE users SET role='{role}' WHERE id={user_id};")
    login = api("POST", "/api/auth/token", payload={"email": email, "password": PASSWORD})
    if login["http_status"] != 200:
        raise RuntimeError(f"login {label} failed: {compact_response(login)}")
    return {"id": user_id, "token": login["body"]["accessToken"], "label": label}


def clean_users(user_ids: list[int]) -> None:
    ids = ",".join(str(v) for v in user_ids)
    mysql(f"""
        DELETE oi FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id IN ({ids});
        DELETE FROM orders WHERE user_id IN ({ids});
        DELETE ci FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id IN ({ids});
        DELETE FROM carts WHERE user_id IN ({ids});
    """)


def create_food(admin: dict, label: str, stock: int) -> dict:
    cat_name = f"G23C_{label}_{uuid.uuid4().hex[:8]}"
    category_id = int(scalar(
        f"INSERT INTO categories(name,description) VALUES('{cat_name}','G2.3 isolated fixture'); SELECT LAST_INSERT_ID();"
    ))
    request = {"categoryId": category_id, "name": f"G23F_{label}_{uuid.uuid4().hex[:8]}",
               "description": "G2.3 concurrency fixture", "price": 10000,
               "imageUrl": None, "stockQuantity": stock, "status": "ACTIVE"}
    response = api("POST", "/api/foods", token=admin["token"], payload=request)
    if response["http_status"] != 201:
        raise RuntimeError(f"food fixture failed: {compact_response(response)}")
    return {"id": int(response["body"]["id"]), "category_id": category_id, "request": request}


def clean_food(food: dict) -> None:
    mysql(f"DELETE FROM foods WHERE id={food['id']}; DELETE FROM categories WHERE id={food['category_id']};")


def add_cart(actor: dict, food_id: int, quantity: int) -> dict:
    return api("POST", "/api/cart/items", token=actor["token"],
               payload={"foodId": food_id, "quantity": quantity})


def checkout_spec(actor: dict) -> dict:
    return {"method": "POST", "path": "/api/orders", "token": actor["token"],
            "payload": {"orderType": "DINE_IN", "tableNumber": "G23",
                        "recipientName": None, "shippingPhone": None,
                        "shippingAddress": None, "paymentMethod": "CASH", "note": "g2.3"}}


def int_scalar(sql: str) -> int:
    return int(scalar(sql) or "0")


def state_for(food_id: int, user_ids: list[int]) -> dict:
    ids = ",".join(str(v) for v in user_ids)
    rows = mysql(f"""
        SELECT COUNT(*) FROM orders WHERE user_id IN ({ids});
        SELECT COALESCE(SUM(oi.quantity),0) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id IN ({ids}) AND oi.food_id={food_id};
        SELECT stock_quantity FROM foods WHERE id={food_id};
        SELECT COUNT(*) FROM carts WHERE user_id IN ({ids});
        SELECT COUNT(*) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id IN ({ids});
        SELECT COALESCE(SUM(ci.quantity),0) FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id IN ({ids}) AND ci.food_id={food_id};
    """).splitlines()
    values = [int(v or "0") for v in rows]
    return dict(zip(("orders", "committed_item_quantity", "stock", "carts", "cart_items", "cart_quantity"), values))


def c1_round(round_id: int, admin: dict, actors: list[dict]) -> dict:
    clean_users([a["id"] for a in actors])
    food = create_food(admin, f"c1r{round_id}", 10)
    try:
        for actor in actors:
            setup = add_cart(actor, food["id"], 7)
            if setup["http_status"] != 200:
                raise RuntimeError(f"C1 cart setup failed: {compact_response(setup)}")
        before = state_for(food["id"], [a["id"] for a in actors])
        responses = concurrent_requests([checkout_spec(a) for a in actors])
        after = state_for(food["id"], [a["id"] for a in actors])
        violations = []
        if after["committed_item_quantity"] > 10:
            violations.append("OVERSELLING: committed quantity exceeds initial stock")
        if after["stock"] != 10 - after["committed_item_quantity"]:
            violations.append("LOST_UPDATE: final stock != initial stock - committed quantity")
        if after["orders"] != sum(r["http_status"] == 201 for r in responses):
            violations.append("HTTP/DB order-count mismatch")
        return {"round": round_id, "initial": before, "responses": responses,
                "final": after, "violations": violations}
    finally:
        clean_users([a["id"] for a in actors])
        clean_food(food)


def c2_round(round_id: int, admin: dict, actor: dict) -> dict:
    clean_users([actor["id"]])
    food = create_food(admin, f"c2r{round_id}", 10)
    try:
        setup = add_cart(actor, food["id"], 2)
        if setup["http_status"] != 200:
            raise RuntimeError(f"C2 cart setup failed: {compact_response(setup)}")
        before = state_for(food["id"], [actor["id"]])
        spec = checkout_spec(actor)
        responses = concurrent_requests([spec, spec])
        after = state_for(food["id"], [actor["id"]])
        violations = []
        if after["orders"] > 1 or after["committed_item_quantity"] > 2:
            violations.append("DOUBLE_CHECKOUT: same cart produced more than one order/cart quantity")
        if after["stock"] != 10 - after["committed_item_quantity"]:
            violations.append("STOCK_MISMATCH: final stock inconsistent with committed order items")
        if after["orders"] and after["cart_items"] != 0:
            violations.append("PARTIAL_CART_MUTATION: committed checkout left cart items")
        return {"round": round_id, "initial": before, "responses": responses,
                "final": after, "violations": violations}
    finally:
        clean_users([actor["id"]])
        clean_food(food)


def c3_round(round_id: int, admin: dict, actor: dict) -> dict:
    clean_users([actor["id"]])
    food = create_food(admin, f"c3r{round_id}", 10)
    try:
        if add_cart(actor, food["id"], 2)["http_status"] != 200:
            raise RuntimeError("C3 cart setup failed")
        created = api(**checkout_spec(actor))
        if created["http_status"] != 201:
            raise RuntimeError(f"C3 order setup failed: {compact_response(created)}")
        order_id = int(created["body"]["id"])
        before = state_for(food["id"], [actor["id"]])
        spec = {"method": "DELETE", "path": f"/api/orders/{order_id}", "token": actor["token"]}
        responses = concurrent_requests([spec, spec])
        after = state_for(food["id"], [actor["id"]])
        order_status = scalar(f"SELECT status FROM orders WHERE id={order_id};")
        violations = []
        if after["stock"] > 10:
            violations.append("DOUBLE_RELEASE: final stock exceeds pre-checkout stock")
        if order_status == "CANCELLED" and after["stock"] != 10:
            violations.append("CANCEL_STOCK_MISMATCH: cancelled order did not restore stock exactly once")
        return {"round": round_id, "order_id": order_id, "initial": before,
                "responses": responses, "final": {**after, "order_status": order_status},
                "violations": violations}
    finally:
        clean_users([actor["id"]])
        clean_food(food)


def c4_round(round_id: int, admin: dict, actor: dict) -> dict:
    clean_users([actor["id"]])
    food = create_food(admin, f"c4r{round_id}", 10)
    try:
        if add_cart(actor, food["id"], 3)["http_status"] != 200:
            raise RuntimeError("C4 cart setup failed")
        before = state_for(food["id"], [actor["id"]])
        update = dict(food["request"])
        update["stockQuantity"] = 20
        specs = [checkout_spec(actor), {"method": "PUT", "path": f"/api/foods/{food['id']}",
                                        "token": admin["token"], "payload": update}]
        responses = concurrent_requests(specs)
        after = state_for(food["id"], [actor["id"]])
        checkout_ok = responses[0]["http_status"] == 201
        serializable_outcomes = [17, 20] if checkout_ok else [20]
        anomalies = []
        if after["stock"] < 0:
            anomalies.append("NEGATIVE_STOCK")
        if after["stock"] not in serializable_outcomes:
            anomalies.append("NON_SERIALIZABLE_FINAL_STOCK_FOR_ABSOLUTE_UPDATE_CONTRACT")
        return {"round": round_id, "initial": before, "responses": responses,
                "final": after, "serializable_final_stock_outcomes": serializable_outcomes,
                "observations": anomalies, "violations": []}
    finally:
        clean_users([actor["id"]])
        clean_food(food)


def c5_round(round_id: int, admin: dict, actor: dict) -> dict:
    clean_users([actor["id"]])
    food = create_food(admin, f"c5r{round_id}", 10)
    try:
        before = state_for(food["id"], [actor["id"]])
        spec = {"method": "POST", "path": "/api/cart/items", "token": actor["token"],
                "payload": {"foodId": food["id"], "quantity": 1}}
        responses = concurrent_requests([spec, spec])
        after = state_for(food["id"], [actor["id"]])
        violations = []
        successes = sum(r["http_status"] == 200 for r in responses)
        if after["carts"] != 1:
            violations.append("CART_CARDINALITY: unique customer cart invariant violated")
        if after["cart_items"] > 1:
            violations.append("CART_ITEM_CARDINALITY: duplicate food rows in one cart")
        if successes == 2 and after["cart_quantity"] != 2:
            violations.append("LOST_CART_ITEM_UPDATE: two successful adds did not produce quantity 2")
        if successes >= 1 and after["cart_quantity"] < 1:
            violations.append("LOST_CART_ITEM: successful add left no item")
        return {"round": round_id, "initial": before, "responses": responses,
                "final": after, "violations": violations}
    finally:
        clean_users([actor["id"]])
        clean_food(food)


def classify(scenario_id: str, rounds: list[dict]) -> dict:
    violation_rounds = [r["round"] for r in rounds if r.get("violations")]
    server_error_rounds = [r["round"] for r in rounds
                           if any((x.get("http_status") or 0) >= 500 or x.get("error") for x in r["responses"])]
    observation_rounds = [r["round"] for r in rounds if r.get("observations")]
    if violation_rounds:
        classification = "CONFIRMED DEFECT"
    elif scenario_id == "C4":
        classification = "INCONCLUSIVE"
    elif server_error_rounds:
        classification = "INCONCLUSIVE"
    else:
        classification = "OBSERVED CORRECT"
    return {"scenario": scenario_id, "classification": classification,
            "rounds_executed": len(rounds), "invariant_violation_rounds": violation_rounds,
            "server_or_transport_error_rounds": server_error_rounds,
            "notable_observation_rounds": observation_rounds}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=15)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    started = utc_now()

    admin = register_actor("admin", "ADMIN")
    actors = {name: register_actor(name) for name in ("c1a", "c1b", "c2", "c3", "c4", "c5")}
    scenario_functions = {
        "C1": lambda n: c1_round(n, admin, [actors["c1a"], actors["c1b"]]),
        "C2": lambda n: c2_round(n, admin, actors["c2"]),
        "C3": lambda n: c3_round(n, admin, actors["c3"]),
        "C4": lambda n: c4_round(n, admin, actors["c4"]),
        "C5": lambda n: c5_round(n, admin, actors["c5"]),
    }
    all_results = {}
    summaries = []
    try:
        for scenario_id, run_round in scenario_functions.items():
            rounds = []
            for round_id in range(1, args.rounds + 1):
                rounds.append(run_round(round_id))
            record = {
                "scenario": scenario_id,
                "method_limitations": [
                    "Barrier synchronizes client worker release, not an in-transaction database barrier.",
                    "HTTP timestamps prove near-simultaneous client attempts but do not prove transaction overlap.",
                    "No application synchronization hook or source/config change was used.",
                ],
                "rounds": rounds,
            }
            record["summary"] = classify(scenario_id, rounds)
            all_results[scenario_id] = record
            summaries.append(record["summary"])
            (output / f"{scenario_id.lower()}-raw.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        clean_users([a["id"] for a in actors.values()])
        ids = ",".join(str(v) for v in [admin["id"], *[a["id"] for a in actors.values()]])
        mysql(f"DELETE FROM users WHERE id IN ({ids});")

    top = {"started_at_utc": started, "finished_at_utc": utc_now(), "base_url": BASE_URL,
           "compose_project": PROJECT, "rounds_per_scenario": args.rounds,
           "concurrency_level": 2, "summaries": summaries}
    (output / "concurrency-summary.json").write_text(
        json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(top, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
