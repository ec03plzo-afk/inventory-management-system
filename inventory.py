#!/usr/bin/env python3
"""
Inventory Management System
---------------------------
A command-line app backed by SQLite (standard library only).

Features:
  - Add, edit, delete, search and list products
  - Stock in / stock out with a full transaction history
  - Low-stock alerts
  - Inventory valuation report
  - CSV export

Run:  python inventory.py
"""

import csv
import sqlite3
from datetime import datetime

DB_FILE = "inventory.db"


# ---------------------------------------------------------------- database --
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                sku          TEXT NOT NULL UNIQUE,
                name         TEXT NOT NULL,
                category     TEXT DEFAULT '',
                quantity     INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                unit_price   REAL NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
                reorder_level INTEGER NOT NULL DEFAULT 5,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL
                            REFERENCES products(id) ON DELETE CASCADE,
                change      INTEGER NOT NULL,
                reason      TEXT DEFAULT '',
                created_at  TEXT NOT NULL
            );
            """
        )


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------- operations --
def add_product(sku, name, category, quantity, unit_price, reorder_level):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO products
               (sku, name, category, quantity, unit_price, reorder_level, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sku, name, category, quantity, unit_price, reorder_level, now()),
        )
        if quantity > 0:
            conn.execute(
                "INSERT INTO transactions (product_id, change, reason, created_at) "
                "VALUES (?, ?, ?, ?)",
                (cur.lastrowid, quantity, "Initial stock", now()),
            )


def find_by_sku(sku):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE sku = ?", (sku,)
        ).fetchone()


def list_products(search=None, low_only=False):
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND (sku LIKE ? OR name LIKE ? OR category LIKE ?)"
        params += [f"%{search}%"] * 3
    if low_only:
        query += " AND quantity <= reorder_level"
    query += " ORDER BY name"
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def update_product(sku, **fields):
    allowed = {"name", "category", "unit_price", "reorder_level"}
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE products SET {sets} WHERE sku = ?", (*fields.values(), sku)
        )


def delete_product(sku):
    with get_conn() as conn:
        conn.execute("DELETE FROM products WHERE sku = ?", (sku,))


def adjust_stock(sku, change, reason=""):
    """Positive change = stock in, negative = stock out."""
    product = find_by_sku(sku)
    if product is None:
        raise ValueError(f"No product with SKU '{sku}'.")
    if product["quantity"] + change < 0:
        raise ValueError(
            f"Not enough stock. Available: {product['quantity']}, requested: {-change}."
        )
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ?",
            (change, product["id"]),
        )
        conn.execute(
            "INSERT INTO transactions (product_id, change, reason, created_at) "
            "VALUES (?, ?, ?, ?)",
            (product["id"], change, reason, now()),
        )


def history(sku=None, limit=20):
    query = """SELECT t.created_at, p.sku, p.name, t.change, t.reason
               FROM transactions t JOIN products p ON p.id = t.product_id"""
    params = []
    if sku:
        query += " WHERE p.sku = ?"
        params.append(sku)
    query += " ORDER BY t.id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def valuation():
    with get_conn() as conn:
        return conn.execute(
            """SELECT COUNT(*) AS items,
                      COALESCE(SUM(quantity), 0) AS units,
                      COALESCE(SUM(quantity * unit_price), 0) AS value
               FROM products"""
        ).fetchone()


def export_csv(path="inventory_export.csv"):
    rows = list_products()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["SKU", "Name", "Category", "Quantity", "Unit Price", "Reorder Level"]
        )
        for r in rows:
            writer.writerow(
                [r["sku"], r["name"], r["category"], r["quantity"],
                 r["unit_price"], r["reorder_level"]]
            )
    return path, len(rows)


# --------------------------------------------------------------------- CLI --
def ask(prompt, cast=str, default=None, allow_blank=False):
    while True:
        raw = input(prompt).strip()
        if raw == "":
            if default is not None:
                return default
            if allow_blank:
                return None
            print("  A value is required.")
            continue
        try:
            return cast(raw)
        except ValueError:
            print(f"  Invalid input, expected {cast.__name__}.")


def print_table(rows):
    if not rows:
        print("  (no products found)")
        return
    header = f"{'SKU':<12}{'Name':<26}{'Category':<14}{'Qty':>6}{'Price':>10}{'Reorder':>9}"
    print(header)
    print("-" * len(header))
    for r in rows:
        flag = "  <-- LOW" if r["quantity"] <= r["reorder_level"] else ""
        print(
            f"{r['sku']:<12}{r['name'][:25]:<26}{r['category'][:13]:<14}"
            f"{r['quantity']:>6}{r['unit_price']:>10.2f}{r['reorder_level']:>9}{flag}"
        )


def menu_add():
    sku = ask("SKU: ")
    if find_by_sku(sku):
        print("  That SKU already exists.")
        return
    name = ask("Name: ")
    category = ask("Category (optional): ", default="")
    qty = ask("Initial quantity [0]: ", int, default=0)
    price = ask("Unit price [0]: ", float, default=0.0)
    reorder = ask("Reorder level [5]: ", int, default=5)
    if qty < 0 or price < 0 or reorder < 0:
        print("  Values cannot be negative.")
        return
    add_product(sku, name, category, qty, price, reorder)
    print("  Product added.")


def menu_edit():
    sku = ask("SKU to edit: ")
    if not find_by_sku(sku):
        print("  No such product.")
        return
    print("  Leave a field blank to keep its current value.")
    update_product(
        sku,
        name=ask("New name: ", allow_blank=True),
        category=ask("New category: ", allow_blank=True),
        unit_price=ask("New unit price: ", float, allow_blank=True),
        reorder_level=ask("New reorder level: ", int, allow_blank=True),
    )
    print("  Product updated.")


def menu_delete():
    sku = ask("SKU to delete: ")
    if not find_by_sku(sku):
        print("  No such product.")
        return
    if input(f"  Delete {sku} and its history? (y/N): ").lower() == "y":
        delete_product(sku)
        print("  Deleted.")


def menu_stock(direction):
    sku = ask("SKU: ")
    qty = ask("Quantity: ", int)
    if qty <= 0:
        print("  Quantity must be positive.")
        return
    reason = ask("Reason (optional): ", default="")
    try:
        adjust_stock(sku, qty * direction, reason)
        print("  Stock updated.")
    except ValueError as e:
        print(f"  Error: {e}")


def menu_history():
    sku = ask("SKU (blank for all): ", allow_blank=True)
    rows = history(sku)
    if not rows:
        print("  (no transactions)")
    for r in rows:
        print(f"  {r['created_at']}  {r['sku']:<10} {r['change']:+5d}  {r['reason']}")


def menu_report():
    v = valuation()
    print(f"  Distinct products : {v['items']}")
    print(f"  Total units       : {v['units']}")
    print(f"  Inventory value   : {v['value']:,.2f}")
    low = list_products(low_only=True)
    print(f"\n  Low-stock items ({len(low)}):")
    print_table(low)


MENU = """
===== INVENTORY MANAGEMENT =====
 1. List all products       6. Stock out (sell/use)
 2. Search products         7. Transaction history
 3. Add product             8. Report & low-stock alerts
 4. Edit product            9. Export to CSV
 5. Stock in (receive)     10. Delete product
 0. Exit
"""


def main():
    init_db()
    actions = {
        "1": lambda: print_table(list_products()),
        "2": lambda: print_table(list_products(ask("Search: "))),
        "3": menu_add,
        "4": menu_edit,
        "5": lambda: menu_stock(+1),
        "6": lambda: menu_stock(-1),
        "7": menu_history,
        "8": menu_report,
        "9": lambda: print("  Exported {1} rows to {0}".format(*export_csv())),
        "10": menu_delete,
    }
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action is None:
            print("  Invalid option.")
            continue
        try:
            action()
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")
        except sqlite3.Error as e:
            print(f"  Database error: {e}")


if __name__ == "__main__":
    main()
