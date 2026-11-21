#!/usr/bin/env python3
"""G2.3 query diagnostics against the isolated Compose MySQL/application."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


PASSWORD = os.environ["G23_ACTOR_PASSWORD"]
HASH = "$2b$10$G62Lilvg88zuj9uaBhyVS.6353AW89LP/D3PEnYridbRObApk.MfW"
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "byteme-g23")
BASE_URL = os.environ.get("BYTEME_BASE_URL", "http://127.0.0.1:18081")
COMPOSE_FILE = os.environ.get("G23_COMPOSE_FILE", "compose.yaml")
OVERRIDE_FILE = os.environ.get("G23_OVERRIDE_FILE", ".local/g2.3/compose.override.yaml")
ENV_FILE = os.environ.get("G23_ENV_FILE", ".local/g2.3/runtime.env")
HTTP_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def compose_prefix() -> list[str]:
    return ["docker", "compose", "--env-file", ENV_FILE, "-p", PROJECT,
            "-f", COMPOSE_FILE, "-f", OVERRIDE_FILE]


def mysql(sql: str, *, root: bool = False) -> str:
    if root:
        shell = 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --batch --raw --skip-column-names -uroot "$MYSQL_DATABASE"'
    else:
        shell = 'MYSQL_PWD="$MYSQL_PASSWORD" mysql --batch --raw --skip-column-names -u"$MYSQL_USER" "$MYSQL_DATABASE"'
    proc = subprocess.run(compose_prefix() + ["exec", "-T", "mysql", "sh", "-lc", shell],
                          input=sql, text=True, encoding="utf-8", capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"mysql exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def scalar(sql: str, *, root: bool = False) -> str:
    rows = mysql(sql, root=root).splitlines()
    return rows[-1] if rows else ""


def api(method: str, path: str, *, token: str | None = None, payload=None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    start = time.perf_counter_ns()
    status = None
    raw = b""
    error = None
    try:
        with HTTP_OPENER.open(request, timeout=60) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    body = None
    if raw:
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = raw.decode("utf-8", errors="replace")[:1000]
    return {"http_status": status, "elapsed_ms": round((time.perf_counter_ns() - start) / 1_000_000, 3),
            "error": error, "body": body}


def register_customer() -> dict:
    nonce = uuid.uuid4().hex[:10]
    email = f"g23.query.{nonce}@example.test"
    phone = "07" + str(int(nonce[:8], 16)).zfill(8)[-8:]
    registered = api("POST", "/api/auth/register", payload={"fullName": "G23 Query Actor", "email": email,
                     "phone": phone, "password": PASSWORD, "confirmPassword": PASSWORD})
    if registered["http_status"] != 201:
        raise RuntimeError(f"register failed: {registered['http_status']} {registered['body']}")
    user_id = int(scalar(f"SELECT id FROM users WHERE email='{email}';"))
    logged_in = api("POST", "/api/auth/token", payload={"email": email, "password": PASSWORD})
    if logged_in["http_status"] != 200:
        raise RuntimeError(f"login failed: {logged_in['http_status']} {logged_in['body']}")
    return {"id": user_id, "token": logged_in["body"]["accessToken"]}


def insert_batches(statements: list[str], batch_size: int = 400) -> None:
    for start in range(0, len(statements), batch_size):
        mysql("START TRANSACTION;\n" + "\n".join(statements[start:start + batch_size]) + "\nCOMMIT;")


def clear_general_log() -> None:
    mysql("SET GLOBAL general_log='OFF'; SET GLOBAL log_output='TABLE'; TRUNCATE TABLE mysql.general_log;", root=True)


def capture_queries(path: str, token: str) -> dict:
    clear_general_log()
    mysql("SET GLOBAL general_log='ON';", root=True)
    response = api("GET", path, token=token)
    mysql("SET GLOBAL general_log='OFF';", root=True)
    raw = mysql("""
        SELECT CONCAT(command_type, CHAR(9), REPLACE(REPLACE(argument, CHAR(10), ' '), CHAR(9), ' '))
        FROM mysql.general_log
        WHERE command_type IN ('Query','Execute')
          AND LOWER(argument) LIKE 'select%'
          AND argument NOT LIKE '%mysql.general_log%'
        ORDER BY event_time;
    """, root=True)
    queries = []
    for line in raw.splitlines():
        command, _, statement = line.partition("\t")
        queries.append({"command_type": command, "sql": statement})
    body = response.pop("body")
    response["content_count"] = len(body.get("content", [])) if isinstance(body, dict) else None
    response["total_elements"] = body.get("totalElements") if isinstance(body, dict) else None
    item_queries = [q for q in queries if "from order_items" in q["sql"].lower()]
    order_queries = [q for q in queries if "from orders" in q["sql"].lower()]
    return {"api": response, "sql_statement_count": len(queries),
            "order_statement_count": len(order_queries), "order_item_statement_count": len(item_queries),
            "statements": queries}


def explain(sql: str) -> dict:
    return {
        "sql": sql,
        "explain_analyze": mysql("EXPLAIN ANALYZE " + sql + ";"),
        "explain_json": mysql("EXPLAIN FORMAT=JSON " + sql + ";"),
    }


def create_category_food(label: str) -> tuple[int, int]:
    category_id = int(scalar(
        f"INSERT INTO categories(name,description) VALUES('G23Q_{label}_{uuid.uuid4().hex[:8]}','query fixture'); SELECT LAST_INSERT_ID();"
    ))
    food_id = int(scalar(
        f"INSERT INTO foods(category_id,name,description,price,stock_quantity,status) "
        f"VALUES({category_id},'G23Q_food_{label}_{uuid.uuid4().hex[:8]}','query fixture',10000,100000,'ACTIVE'); "
        "SELECT LAST_INSERT_ID();"
    ))
    return category_id, food_id


def q1(actor: dict, output: pathlib.Path) -> dict:
    category_id, food_id = create_category_food("q1")
    orders = []
    items = []
    for i in range(60):
        created = f"2026-10-{1 + i // 24:02d} {i % 24:02d}:00:00.000000"
        orders.append(
            "INSERT INTO orders(user_id,status,order_type,table_number,payment_method,created_at,updated_at) "
            f"VALUES({actor['id']},'PENDING','DINE_IN','Q1','CASH','{created}','{created}'); SET @oid=LAST_INSERT_ID(); "
            f"INSERT INTO order_items(order_id,food_id,food_name,unit_price,quantity,created_at) VALUES(@oid,{food_id},'Q1 item',10000,1,'{created}');"
        )
    insert_batches(orders, 100)
    measurements = []
    for size in (1, 5, 20, 50):
        measurements.append({"page_size": size, **capture_queries(f"/api/orders?page=0&size={size}", actor["token"])})
    order_id = int(scalar(f"SELECT id FROM orders WHERE user_id={actor['id']} ORDER BY id LIMIT 1;"))
    detail = capture_queries(f"/api/orders/{order_id}", actor["token"])
    nplus1 = all(m["order_item_statement_count"] == m["api"]["content_count"] for m in measurements)
    grows = measurements[-1]["order_item_statement_count"] > measurements[0]["order_item_statement_count"]
    result = {"investigation": "Q1", "dataset_orders": 60, "items_per_order": 1,
              "measurements": measurements, "detail_measurement": detail,
              "classification": "CONFIRMED DEFECT" if nplus1 and grows else "INCONCLUSIVE",
              "finding": "N+1 observed: one order_items SELECT per listed order" if nplus1 and grows
                         else "Telemetry did not establish the N+1 growth pattern"}
    (output / "q1-order-listing.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mysql(f"DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id={actor['id']}); "
          f"DELETE FROM orders WHERE user_id={actor['id']}; DELETE FROM foods WHERE id={food_id}; DELETE FROM categories WHERE id={category_id};")
    return result


def q2(actor: dict, output: pathlib.Path) -> dict:
    category_id = int(scalar(
        f"INSERT INTO categories(name,description) VALUES('G23Q_Q2_{uuid.uuid4().hex[:8]}','query fixture'); SELECT LAST_INSERT_ID();"
    ))
    levels = []
    inserted = 0
    for target in (100, 1000, 5000):
        rows = []
        for i in range(inserted, target):
            marker = "needle" if i % 10 == 0 else "haystack"
            rows.append(
                "INSERT INTO foods(category_id,name,description,price,stock_quantity,status) "
                f"VALUES({category_id},'G23Q2_{i:05d}_{marker}','diagnostic {marker}',10000,100,'ACTIVE');"
            )
        insert_batches(rows)
        inserted = target
        mysql("ANALYZE TABLE foods;")
        plain_sql = ("SELECT id,category_id,name,description,price,image_url,stock_quantity,status,created_at,updated_at "
                     "FROM foods WHERE status='ACTIVE' AND (LOWER(name) LIKE '%needle%' OR LOWER(description) LIKE '%needle%') ORDER BY id")
        category_sql = ("SELECT id,category_id,name,description,price,image_url,stock_quantity,status,created_at,updated_at "
                        f"FROM foods WHERE status='ACTIVE' AND category_id={category_id} "
                        "AND (LOWER(name) LIKE '%needle%' OR LOWER(description) LIKE '%needle%') ORDER BY id")
        api_plain = api("GET", "/api/foods/search?q=needle", token=actor["token"])
        api_category = api("GET", f"/api/foods/search?q=needle&categoryId={category_id}", token=actor["token"])
        levels.append({"food_rows_in_fixture": target,
                       "total_food_rows": int(scalar("SELECT COUNT(*) FROM foods;")),
                       "api_plain": {"http_status": api_plain["http_status"], "elapsed_ms": api_plain["elapsed_ms"],
                                     "result_count": len(api_plain["body"]) if isinstance(api_plain["body"], list) else None},
                       "api_category": {"http_status": api_category["http_status"], "elapsed_ms": api_category["elapsed_ms"],
                                        "result_count": len(api_category["body"]) if isinstance(api_category["body"], list) else None},
                       "plain_plan": explain(plain_sql), "category_plan": explain(category_sql)})
    result = {"investigation": "Q2", "levels": levels,
              "show_index": mysql("SHOW INDEX FROM foods;"),
              "classification": "INCONCLUSIVE",
              "finding": "Execution-plan/index facts are diagnostic; no representative workload or official benchmark threshold was defined."}
    (output / "q2-food-search.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    mysql(f"DELETE FROM foods WHERE category_id={category_id}; DELETE FROM categories WHERE id={category_id};")
    return result


def q3(actor: dict, output: pathlib.Path) -> dict:
    category_id, food_id = create_category_food("q3")
    synthetic_users = []
    for i in range(20):
        email = f"g23.q3.user{i:02d}@example.test"
        phone = f"06{i:08d}"[-10:]
        user_id = int(scalar(
            "INSERT INTO users(full_name,email,phone,password_hash,role,status) "
            f"VALUES('G23 Q3 {i}','{email}','{phone}','{HASH}','CUSTOMER','ACTIVE'); SELECT LAST_INSERT_ID();"
        ))
        synthetic_users.append(user_id)
    user_cycle = [actor["id"], *synthetic_users]
    levels = []
    inserted = 0
    statuses = ("PENDING", "CONFIRMED", "PROCESSING", "SHIPPING", "COMPLETED", "CANCELLED")
    for target in (100, 1000, 5000):
        statements = []
        for i in range(inserted, target):
            user_id = user_cycle[i % len(user_cycle)]
            status = statuses[i % len(statuses)]
            order_type = "DINE_IN" if i % 2 == 0 else "DELIVERY"
            payment = "CASH" if order_type == "DINE_IN" else "COD"
            table = "'Q3'" if order_type == "DINE_IN" else "NULL"
            recipient = "NULL" if order_type == "DINE_IN" else "'Q3 recipient'"
            phone = "NULL" if order_type == "DINE_IN" else "'0900000000'"
            address = "NULL" if order_type == "DINE_IN" else "'Q3 address'"
            created = f"2026-10-{1 + (i // 864) % 6:02d} {(i // 36) % 24:02d}:{i % 60:02d}:00.000000"
            statements.append(
                "INSERT INTO orders(user_id,status,order_type,table_number,recipient_name,shipping_phone,shipping_address,payment_method,created_at,updated_at) "
                f"VALUES({user_id},'{status}','{order_type}',{table},{recipient},{phone},{address},'{payment}','{created}','{created}'); "
                "SET @oid=LAST_INSERT_ID(); "
                f"INSERT INTO order_items(order_id,food_id,food_name,unit_price,quantity,created_at) VALUES(@oid,{food_id},'Q3 item',10000,1,'{created}');"
            )
        insert_batches(statements, 150)
        inserted = target
        mysql("ANALYZE TABLE orders;")
        owner_count = int(scalar(f"SELECT COUNT(*) FROM orders WHERE user_id={actor['id']};"))
        list_sql = ("SELECT id,user_id,status,order_type,table_number,recipient_name,shipping_phone,shipping_address,"
                    "payment_method,note,confirmed_by,confirmed_at,cancelled_at,completed_at,created_at,updated_at "
                    f"FROM orders WHERE user_id={actor['id']} AND status IN ('PENDING','CONFIRMED','PROCESSING','SHIPPING','COMPLETED','CANCELLED') "
                    "ORDER BY created_at DESC,id DESC LIMIT 20")
        filtered_sql = ("SELECT id,user_id,status,order_type,created_at,updated_at FROM orders "
                        f"WHERE user_id={actor['id']} AND status='PENDING' AND order_type='DINE_IN' "
                        "ORDER BY created_at DESC,id DESC LIMIT 20")
        count_sql = (f"SELECT COUNT(*) FROM orders WHERE user_id={actor['id']} "
                     "AND status IN ('PENDING','CONFIRMED','PROCESSING','SHIPPING','COMPLETED','CANCELLED')")
        api_measure = capture_queries("/api/orders?page=0&size=20", actor["token"])
        filtered_api = api("GET", "/api/orders?status=PENDING&orderType=DINE_IN&page=0&size=20", token=actor["token"])
        levels.append({"total_synthetic_orders": target, "actor_orders": owner_count,
                       "api_query_count": {key: api_measure[key] for key in
                                           ("api", "sql_statement_count", "order_statement_count", "order_item_statement_count")},
                       "filtered_api": {"http_status": filtered_api["http_status"], "elapsed_ms": filtered_api["elapsed_ms"],
                                        "content_count": len(filtered_api["body"].get("content", [])) if isinstance(filtered_api["body"], dict) else None},
                       "list_plan": explain(list_sql), "filtered_plan": explain(filtered_sql),
                       "count_plan": explain(count_sql)})
    offset_sql = ("SELECT id,user_id,status,order_type,created_at,updated_at FROM orders "
                  f"WHERE user_id={actor['id']} AND status IN ('PENDING','CONFIRMED','PROCESSING','SHIPPING','COMPLETED','CANCELLED') "
                  "ORDER BY created_at DESC,id DESC LIMIT 100,20")
    result = {"investigation": "Q3", "levels": levels, "offset_page_plan": explain(offset_sql),
              "show_index": mysql("SHOW INDEX FROM orders;"), "classification": "INCONCLUSIVE",
              "finding": "Plans and query counts were measured, but G2.3 is not an official workload benchmark and has no bottleneck threshold."}
    (output / "q3-order-filter-pagination.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    all_users = ",".join(str(v) for v in [actor["id"], *synthetic_users])
    mysql(f"DELETE oi FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id IN ({all_users}); "
          f"DELETE FROM orders WHERE user_id IN ({all_users}); DELETE FROM foods WHERE id={food_id}; "
          f"DELETE FROM categories WHERE id={category_id}; DELETE FROM users WHERE id IN ({','.join(map(str, synthetic_users))});")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    actor = register_customer()
    results = []
    try:
        results.append(q1(actor, output))
        results.append(q2(actor, output))
        results.append(q3(actor, output))
    finally:
        mysql("SET GLOBAL general_log='OFF';", root=True)
        mysql(f"DELETE oi FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.user_id={actor['id']}; "
              f"DELETE FROM orders WHERE user_id={actor['id']}; DELETE ci FROM cart_items ci JOIN carts c ON c.id=ci.cart_id WHERE c.user_id={actor['id']}; "
              f"DELETE FROM carts WHERE user_id={actor['id']}; DELETE FROM users WHERE id={actor['id']};")
    summary = {"started_at_utc": started, "finished_at_utc": utc_now(), "base_url": BASE_URL,
               "compose_project": PROJECT,
               "results": [{"investigation": r["investigation"], "classification": r["classification"],
                            "finding": r["finding"]} for r in results],
               "limitations": ["Synthetic isolated dataset, diagnostic only; not the G2.5 benchmark.",
                               "Client latency is single-run diagnostic latency without warm-up/control protocol.",
                               "EXPLAIN ANALYZE statements ran only on the isolated database; no indexes were added."]}
    (output / "query-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
