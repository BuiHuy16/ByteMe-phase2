#!/usr/bin/env python3
"""Prepare/reset a deterministic dataset in an explicitly isolated benchmark project."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[2]
PROFILES_PATH = pathlib.Path(__file__).with_name("profiles.json")
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def require_isolated(project: str, db_name: str) -> None:
    allowed_project = project.startswith("byteme-g24-") or project.startswith("byteme-benchmark-")
    allowed_db = db_name.startswith("byteme_g24_") or db_name.startswith("byteme_benchmark_")
    if not allowed_project or not allowed_db:
        raise SystemExit(f"Refusing destructive reset outside benchmark namespace: project={project}, db={db_name}")


def compose_prefix(args) -> list[str]:
    return ["docker", "compose", "--env-file", args.env_file, "-p", args.project,
            "-f", "compose.yaml", "-f", "benchmarks/phase2/compose.benchmark.yaml"]


def mysql(args, sql: str) -> str:
    if args.db_mode == "direct":
        password = os.environ.get(args.mysql_password_env)
        if password is None:
            raise RuntimeError(f"Required password environment variable is absent: {args.mysql_password_env}")
        environment = os.environ.copy()
        environment["MYSQL_PWD"] = password
        command = [args.mysql_bin, "--protocol=TCP", "--batch", "--raw", "--skip-column-names",
                   "--host", args.mysql_host, "--port", str(args.mysql_port),
                   "--user", args.mysql_user, args.mysql_database]
        proc = subprocess.run(command, cwd=ROOT, input=sql, text=True, encoding="utf-8",
                              capture_output=True, env=environment)
    else:
        shell = 'MYSQL_PWD="$MYSQL_PASSWORD" mysql --batch --raw --skip-column-names -u"$MYSQL_USER" "$MYSQL_DATABASE"'
        proc = subprocess.run(compose_prefix(args) + ["exec", "-T", "mysql", "sh", "-lc", shell],
                              cwd=ROOT, input=sql, text=True, encoding="utf-8", capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"mysql exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def api(base_url: str, method: str, path: str, payload=None, token: str | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with HTTP.open(request, timeout=30) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    body = json.loads(raw.decode("utf-8")) if raw else None
    return {"status": status, "body": body}


def batches(args, statements: list[str], size: int = 300) -> None:
    for start in range(0, len(statements), size):
        mysql(args, "START TRANSACTION;\n" + "\n".join(statements[start:start + size]) + "\nCOMMIT;")


def reset_database(args) -> None:
    mysql(args, """
        SET FOREIGN_KEY_CHECKS=0;
        TRUNCATE TABLE order_items;
        TRUNCATE TABLE orders;
        TRUNCATE TABLE cart_items;
        TRUNCATE TABLE carts;
        TRUNCATE TABLE foods;
        TRUNCATE TABLE categories;
        TRUNCATE TABLE users;
        SET FOREIGN_KEY_CHECKS=1;
    """)


def register(args, label: str, phone_index: int, password: str, role: str = "CUSTOMER",
             reusable: dict | None = None) -> dict:
    email = f"bench.{label}@example.test"
    phone = f"09{phone_index:08d}"
    result = api(args.base_url, "POST", "/api/auth/register", {
        "fullName": f"Benchmark {label}", "email": email, "phone": phone,
        "password": password, "confirmPassword": password,
    })
    if result["status"] != 201:
        raise RuntimeError(f"register {label}: HTTP {result['status']} {result['body']}")
    user_id = int(mysql(args, f"SELECT id FROM users WHERE email='{email}';").splitlines()[-1])
    if role != "CUSTOMER":
        mysql(args, f"UPDATE users SET role='{role}' WHERE id={user_id};")
    if reusable is not None:
        expected = {"id": user_id, "label": label, "role": role}
        actual = {key: reusable.get(key) for key in expected}
        if actual != expected or not isinstance(reusable.get("token"), str) or not reusable["token"]:
            raise RuntimeError(f"reusable actor identity mismatch for {label}: {actual} != {expected}")
        return {**expected, "token": reusable["token"]}
    login = api(args.base_url, "POST", "/api/auth/token", {"email": email, "password": password})
    if login["status"] != 200:
        raise RuntimeError(f"login {label}: HTTP {login['status']} {login['body']}")
    return {"id": user_id, "label": label, "role": role, "token": login["body"]["accessToken"]}


def actor_specs(profile: dict) -> list[tuple[str, int, str]]:
    return ([('admin', 1, 'ADMIN'), ('read', 2, 'CUSTOMER')]
            + [(f"write{i:02d}", 100 + i, "CUSTOMER") for i in range(profile["write_actors"])]
            + [(label, 500 + i, "CUSTOMER") for i, label in enumerate(
                ("c1a", "c1b", "c2", "c4")[:profile["contention_actors"]])])


def flatten_actors(document: dict) -> list[dict]:
    return ([document.get("admin", {}), document.get("read", {})]
            + list(document.get("write", [])) + list(document.get("contention", [])))


def load_reusable_actors(path: pathlib.Path, profile_name: str, profile: dict) -> dict[str, dict] | None:
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"existing runtime actor fixture is unreadable: {path}") from exc
    if document.get("profile") != profile_name:
        raise RuntimeError(f"existing runtime actor profile mismatch: {document.get('profile')} != {profile_name}")
    actors = flatten_actors(document)
    expected = {label: role for label, _, role in actor_specs(profile)}
    actual: dict[str, dict] = {}
    for actor in actors:
        label = actor.get("label")
        if not isinstance(label, str) or label in actual:
            raise RuntimeError(f"existing runtime actor fixture has invalid/duplicate label: {label!r}")
        actual[label] = actor
    if set(actual) != set(expected):
        raise RuntimeError(f"existing runtime actor labels mismatch: {sorted(actual)} != {sorted(expected)}")
    for label, role in expected.items():
        actor = actual[label]
        if actor.get("role") != role or not isinstance(actor.get("id"), int) or actor["id"] <= 0:
            raise RuntimeError(f"existing runtime actor identity invalid: {label}")
        if not isinstance(actor.get("token"), str) or not actor["token"]:
            raise RuntimeError(f"existing runtime actor token missing: {label}")
    return actual


def validate_reused_tokens(args, actors: list[dict]) -> None:
    for actor in actors:
        if actor["role"] == "ADMIN":
            path, expected_status = "/api/orders?page=0&size=1", 403
        else:
            path, expected_status = "/api/cart", 200
        result = api(args.base_url, "GET", path, token=actor["token"])
        if result["status"] != expected_status:
            raise RuntimeError(
                f"reused token validation {actor['label']}: HTTP {result['status']} "
                f"expected {expected_status} {result['body']}")


def prepare(args, profile: dict) -> dict:
    password = os.environ.get("BENCH_ACTOR_PASSWORD")
    if not password:
        raise SystemExit("BENCH_ACTOR_PASSWORD is required and is never written to evidence")
    runtime_path = pathlib.Path(args.runtime_actors)
    reusable = load_reusable_actors(runtime_path, args.profile, profile)
    reset_database(args)

    category_rows = [
        f"INSERT INTO categories(id,name,description) VALUES({i},'BENCH_CATEGORY_{i:02d}','benchmark fixture');"
        for i in range(1, profile["categories"] + 1)
    ]
    batches(args, category_rows)

    food_rows = []
    for i in range(1, profile["read_foods"] + 1):
        category = 1 + (i - 1) % profile["categories"]
        marker = "needle" if i % 10 == 0 else "haystack"
        food_rows.append(
            "INSERT INTO foods(id,category_id,name,description,price,stock_quantity,status) "
            f"VALUES({i},{category},'BENCH_READ_{i:05d}_{marker}','search {marker}',10000,1000000,'ACTIVE');"
        )
    batches(args, food_rows)

    admin = register(args, "admin", 1, password, "ADMIN", reusable.get("admin") if reusable else None)
    read_actor = register(args, "read", 2, password, reusable=reusable.get("read") if reusable else None)
    write_actors = [register(args, f"write{i:02d}", 100 + i, password,
                             reusable=reusable.get(f"write{i:02d}") if reusable else None)
                    for i in range(profile["write_actors"])]
    contention_labels = ("c1a", "c1b", "c2", "c4")
    contention = [register(args, label, 500 + i, password,
                           reusable=reusable.get(label) if reusable else None)
                  for i, label in enumerate(contention_labels[:profile["contention_actors"]])]

    next_food = profile["read_foods"] + 1
    write_foods = []
    write_rows = []
    for index, actor in enumerate(write_actors):
        food_id = next_food + index
        write_foods.append({"actor_id": actor["id"], "food_id": food_id})
        write_rows.append(
            "INSERT INTO foods(id,category_id,name,description,price,stock_quantity,status) "
            f"VALUES({food_id},1,'BENCH_WRITE_{index:03d}','dedicated write food',12000,{profile['write_stock']},'ACTIVE');"
        )
    shared_food_id = next_food + len(write_actors)
    write_rows.append(
        "INSERT INTO foods(id,category_id,name,description,price,stock_quantity,status) "
        f"VALUES({shared_food_id},1,'BENCH_SHARED_STOCK','contention fixture',15000,{profile['shared_stock']},'ACTIVE');"
    )
    batches(args, write_rows)

    order_rows = []
    base_time = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)
    item_foods = list(range(1, profile["items_per_order"] + 1))
    for i in range(profile["read_orders"]):
        created = (base_time + dt.timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S.000000")
        order_rows.append(
            "INSERT INTO orders(user_id,status,order_type,table_number,payment_method,created_at,updated_at) "
            f"VALUES({read_actor['id']},'PENDING','DINE_IN','R{i % 100:02d}','CASH','{created}','{created}'); "
            "SET @benchmark_order_id=LAST_INSERT_ID(); " + " ".join(
                "INSERT INTO order_items(order_id,food_id,food_name,unit_price,quantity,created_at) "
                f"VALUES(@benchmark_order_id,{food_id},'BENCH_READ_{food_id:05d}',10000,1,'{created}');"
                for food_id in item_foods
            )
        )
    batches(args, order_rows, 100)

    actors = {
        "profile": args.profile,
        "admin": admin,
        "read": read_actor,
        "write": [{**actor, "food_id": write_foods[i]["food_id"]} for i, actor in enumerate(write_actors)],
        "contention": contention,
        "shared_food": {"id": shared_food_id, "category_id": 1, "name": "BENCH_SHARED_STOCK",
                        "description": "contention fixture", "price": 15000,
                        "initial_stock": profile["shared_stock"], "status": "ACTIVE"},
    }
    all_actors = flatten_actors(actors)
    if reusable:
        validate_reused_tokens(args, all_actors)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(actors, ensure_ascii=False, indent=2), encoding="utf-8")
    actor_count = len(all_actors)
    return {
        "token_strategy": "initial_login" if reusable is None else "reuse_initial_tokens",
        "actor_count": actor_count,
        "login_requests": actor_count if reusable is None else 0,
        "reused_tokens": 0 if reusable is None else actor_count,
        "live_token_validations": 0 if reusable is None else actor_count,
    }


def table_digest(args, table: str, columns: str) -> str:
    raw = mysql(args, f"SELECT {columns} FROM {table} ORDER BY id;")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evaluate_invariants(profile: dict, counts: dict[str, int], *, read_orders: int,
                        read_order_items: int, shared_stock: int, orphan_order_items: int,
                        orphan_cart_items: int, negative_food_stock: int,
                        invalid_cart_quantities: int, invalid_order_quantities: int,
                        validation_phase: str) -> dict[str, bool]:
    """Validate immutable fixtures plus phase-appropriate database state."""
    expected_users = 2 + profile["write_actors"] + profile["contention_actors"]
    expected_foods = profile["read_foods"] + profile["write_actors"] + 1
    expected_items = profile["read_orders"] * profile["items_per_order"]
    invariants = {
        "expected_user_count": counts["users"] == expected_users,
        "expected_category_count": counts["categories"] == profile["categories"],
        "expected_food_count": counts["foods"] == expected_foods,
        "read_fixture_orders_preserved": read_orders == profile["read_orders"],
        "read_fixture_order_items_preserved": read_order_items == expected_items,
        "shared_stock_matches_profile": shared_stock == profile["shared_stock"],
        "no_orphan_order_items": orphan_order_items == 0,
        "no_orphan_cart_items": orphan_cart_items == 0,
        "no_negative_food_stock": negative_food_stock == 0,
        "positive_cart_item_quantities": invalid_cart_quantities == 0,
        "positive_order_item_quantities": invalid_order_quantities == 0,
    }
    if validation_phase == "initial":
        invariants.update({
            "initial_total_orders_exact": counts["orders"] == profile["read_orders"],
            "initial_total_order_items_exact": counts["order_items"] == expected_items,
            "initial_carts_empty": counts["carts"] == 0 and counts["cart_items"] == 0,
        })
    elif validation_phase == "post_workload":
        invariants.update({
            "post_total_orders_not_below_fixture": counts["orders"] >= profile["read_orders"],
            "post_total_order_items_not_below_fixture": counts["order_items"] >= expected_items,
        })
    else:
        raise ValueError(f"Unknown validation phase: {validation_phase}")
    return invariants


def build_manifest(args, profile: dict, validation_phase: str) -> dict:
    actual_db = mysql(args, "SELECT DATABASE();").splitlines()[-1]
    require_isolated(args.project, actual_db)
    counts_raw = mysql(args, """
        SELECT 'users',COUNT(*) FROM users UNION ALL
        SELECT 'categories',COUNT(*) FROM categories UNION ALL
        SELECT 'foods',COUNT(*) FROM foods UNION ALL
        SELECT 'carts',COUNT(*) FROM carts UNION ALL
        SELECT 'cart_items',COUNT(*) FROM cart_items UNION ALL
        SELECT 'orders',COUNT(*) FROM orders UNION ALL
        SELECT 'order_items',COUNT(*) FROM order_items;
    """)
    counts = {line.split("\t")[0]: int(line.split("\t")[1]) for line in counts_raw.splitlines()}
    digests = {
        "users": table_digest(args, "users", "id,full_name,email,phone,role,status"),
        "categories": table_digest(args, "categories", "id,name,COALESCE(description,'')"),
        "foods": table_digest(args, "foods", "id,category_id,name,COALESCE(description,''),price,stock_quantity,status"),
        "carts": table_digest(args, "carts", "id,user_id"),
        "cart_items": table_digest(args, "cart_items", "id,cart_id,food_id,quantity"),
        "orders": table_digest(args, "orders", "id,user_id,status,order_type,COALESCE(table_number,''),payment_method,created_at"),
        "order_items": table_digest(args, "order_items", "id,order_id,food_id,food_name,unit_price,quantity"),
    }
    overall = hashlib.sha256(json.dumps({"counts": counts, "digests": digests}, sort_keys=True).encode()).hexdigest()
    shared_stock = int(mysql(args, "SELECT stock_quantity FROM foods WHERE name='BENCH_SHARED_STOCK';").splitlines()[-1])
    orphan_items = int(mysql(args, "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON o.id=oi.order_id WHERE o.id IS NULL;").splitlines()[-1])
    orphan_cart_items = int(mysql(args, "SELECT COUNT(*) FROM cart_items ci LEFT JOIN carts c ON c.id=ci.cart_id WHERE c.id IS NULL;").splitlines()[-1])
    read_orders = int(mysql(args, "SELECT COUNT(*) FROM orders o JOIN users u ON u.id=o.user_id WHERE u.email='bench.read@example.test';").splitlines()[-1])
    read_order_items = int(mysql(args, "SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN users u ON u.id=o.user_id WHERE u.email='bench.read@example.test';").splitlines()[-1])
    negative_stock = int(mysql(args, "SELECT COUNT(*) FROM foods WHERE stock_quantity < 0;").splitlines()[-1])
    invalid_cart_quantities = int(mysql(args, "SELECT COUNT(*) FROM cart_items WHERE quantity <= 0;").splitlines()[-1])
    invalid_order_quantities = int(mysql(args, "SELECT COUNT(*) FROM order_items WHERE quantity <= 0;").splitlines()[-1])
    invariants = evaluate_invariants(
        profile, counts, read_orders=read_orders, read_order_items=read_order_items,
        shared_stock=shared_stock, orphan_order_items=orphan_items,
        orphan_cart_items=orphan_cart_items, negative_food_stock=negative_stock,
        invalid_cart_quantities=invalid_cart_quantities,
        invalid_order_quantities=invalid_order_quantities, validation_phase=validation_phase,
    )
    return {
        "generated_at_utc": utc_now(), "profile": args.profile, "profile_parameters": profile,
        "execution_mode": args.db_mode, "benchmark_project": args.project,
        "validation_phase": validation_phase,
        "compose_project": args.project, "database": actual_db, "counts": counts,
        "logical_sha256": digests, "overall_sha256": overall,
        "invariants": invariants, "all_invariants_pass": all(invariants.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("prepare", "snapshot"), default="prepare")
    parser.add_argument("--profile", choices=("smoke", "standard"), required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file")
    parser.add_argument("--db-mode", choices=("compose", "direct"), default="compose")
    parser.add_argument("--mysql-bin", default="mysql")
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user")
    parser.add_argument("--mysql-database")
    parser.add_argument("--mysql-password-env", default="BENCH_DB_PASSWORD")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--runtime-actors", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    profile = profiles[args.profile]
    if args.db_mode == "direct":
        if not args.mysql_user or not args.mysql_database:
            parser.error("--mysql-user and --mysql-database are required in direct mode")
        db_name = args.mysql_database
    else:
        if not args.env_file:
            parser.error("--env-file is required in compose mode")
        env_lines = pathlib.Path(args.env_file).read_text(encoding="utf-8").splitlines()
        db_name = next(line.split("=", 1)[1] for line in env_lines if line.startswith("DB_NAME="))
    require_isolated(args.project, db_name)
    preparation = prepare(args, profile) if args.mode == "prepare" else None
    validation_phase = "initial" if args.mode == "prepare" else "post_workload"
    manifest = build_manifest(args, profile, validation_phase)
    if preparation is not None:
        manifest["preparation_authentication"] = preparation
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"profile": args.profile, "mode": args.mode,
                      "overall_sha256": manifest["overall_sha256"],
                      "counts": manifest["counts"],
                      "all_invariants_pass": manifest["all_invariants_pass"]}, indent=2))
    return 0 if manifest["all_invariants_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
