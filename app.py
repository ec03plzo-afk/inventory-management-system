from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
import os
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        url = DATABASE_URL.replace('postgres://', 'postgresql://')
        conn = psycopg2.connect(url)
        return conn, 'pg'
    else:
        conn = sqlite3.connect('inventory.db')
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

def init_db():
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                product_id INTEGER,
                product_name VARCHAR(255) NOT NULL,
                supplier_name VARCHAR(255) DEFAULT 'General Supplier',
                quantity INTEGER NOT NULL,
                purchase_date VARCHAR(100) NOT NULL
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_id INTEGER,
                product_name VARCHAR(255) NOT NULL,
                customer_name VARCHAR(255) DEFAULT 'Walk-in',
                quantity INTEGER NOT NULL,
                order_date VARCHAR(100) NOT NULL
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                contact_person VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                address TEXT
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(50),
                address TEXT
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                item VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL,
                category VARCHAR(255) DEFAULT 'General'
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'Staff'
            );
        ''')
        cur.execute("SELECT * FROM users WHERE username = %s;", ('admin@gmail.com',))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s);", ('admin@gmail.com', 'password123', 'Admin'))
        conn.commit()
        cur.close()
    else:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                supplier_name TEXT DEFAULT 'General Supplier',
                quantity INTEGER NOT NULL,
                purchase_date TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                customer_name TEXT DEFAULT 'Walk-in',
                quantity INTEGER NOT NULL,
                order_date TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                address TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                category TEXT DEFAULT 'General'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'Staff'
            )
        ''')
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin@gmail.com',)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('admin@gmail.com', 'password123', 'Admin'))
        conn.commit()
    conn.close()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn, db_type = get_db_connection()
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s AND password = %s;", (username, password))
            user = cur.fetchone()
            cur.close()
        else:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Username or Password!')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM inventory ORDER BY id;")
        inventory = cur.fetchall()
        cur.execute("SELECT * FROM categories ORDER BY id;")
        categories_list = cur.fetchall()
        cur.execute("SELECT * FROM customers ORDER BY id;")
        customers_list = cur.fetchall()
        cur.execute("SELECT * FROM suppliers ORDER BY id;")
        suppliers_list = cur.fetchall()
        cur.execute("SELECT * FROM orders ORDER BY id;")
        orders_list = cur.fetchall()
        cur.execute("SELECT * FROM purchases ORDER BY id;")
        purchases_list = cur.fetchall()
        cur.execute("SELECT * FROM users ORDER BY id;")
        users_list = cur.fetchall()
        cur.close()
    else:
        inventory = conn.execute('SELECT * FROM inventory').fetchall()
        categories_list = conn.execute('SELECT * FROM categories').fetchall()
        customers_list = conn.execute('SELECT * FROM customers').fetchall()
        suppliers_list = conn.execute('SELECT * FROM suppliers').fetchall()
        orders_list = conn.execute('SELECT * FROM orders').fetchall()
        purchases_list = conn.execute('SELECT * FROM purchases').fetchall()
        users_list = conn.execute('SELECT * FROM users').fetchall()
        
    total_products = len(inventory)
    total_categories = len(categories_list)
    total_customers = len(customers_list)
    total_suppliers = len(suppliers_list)
    total_orders = len(orders_list)
    total_purchases = len(purchases_list)
    total_users = len(users_list)
    conn.close()
    
    return render_template(
        'dashboard.html', 
        total_products=total_products, 
        total_categories=total_categories,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        total_orders=total_orders,
        total_purchases=total_purchases,
        total_users=total_users
    )

# --- USER REGISTRATION MODULE ---
@app.route('/users')
def users():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users ORDER BY id DESC;")
        users_list = cur.fetchall()
        cur.close()
    else:
        users_list = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('users.html', users=users_list)

@app.route('/users/add', methods=['POST'])
def add_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'Staff')
    
    if username and password:
        conn, db_type = get_db_connection()
        try:
            if db_type == 'pg':
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s);", (username, password, role))
                conn.commit()
                cur.close()
            else:
                conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
                conn.commit()
        except Exception as e:
            flash("Username already exists!")
        conn.close()
        
    return redirect(url_for('users'))

@app.route('/users/delete/<int:id>', methods=['POST'])
def delete_user(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM users WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('users'))

# --- PURCHASE MODULE ---
@app.route('/purchases')
def purchases():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM purchases ORDER BY id DESC;")
        purchases_list = cur.fetchall()
        cur.execute("SELECT * FROM inventory ORDER BY item;")
        products_list = cur.fetchall()
        cur.execute("SELECT * FROM suppliers ORDER BY name;")
        suppliers_list = cur.fetchall()
        cur.close()
    else:
        purchases_list = conn.execute('SELECT * FROM purchases ORDER BY id DESC').fetchall()
        products_list = conn.execute('SELECT * FROM inventory ORDER BY item').fetchall()
        suppliers_list = conn.execute('SELECT * FROM suppliers ORDER BY name').fetchall()
    conn.close()
    
    return render_template('purchases.html', purchases=purchases_list, products=products_list, suppliers=suppliers_list)

@app.route('/purchases/add', methods=['POST'])
def add_purchase():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    product_id = request.form.get('product_id')
    supplier_name = request.form.get('supplier_name', 'General Supplier')
    qty_str = request.form.get('quantity')
    
    if product_id and qty_str:
        qty = int(qty_str)
        conn, db_type = get_db_connection()
        
        if db_type == 'pg':
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM inventory WHERE id = %s;", (product_id,))
            prod = cur.fetchone()
            
            if prod:
                new_qty = prod['quantity'] + qty
                cur.execute("UPDATE inventory SET quantity = %s WHERE id = %s;", (new_qty, product_id))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("INSERT INTO purchases (product_id, product_name, supplier_name, quantity, purchase_date) VALUES (%s, %s, %s, %s, %s);",
                            (product_id, prod['item'], supplier_name, qty, now_str))
                conn.commit()
            cur.close()
        else:
            prod = conn.execute('SELECT * FROM inventory WHERE id = ?', (product_id,)).fetchone()
            if prod:
                new_qty = prod['quantity'] + qty
                conn.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (new_qty, product_id))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute('INSERT INTO purchases (product_id, product_name, supplier_name, quantity, purchase_date) VALUES (?, ?, ?, ?, ?)',
                             (product_id, prod['item'], supplier_name, qty, now_str))
                conn.commit()
        conn.close()
        
    return redirect(url_for('purchases'))

@app.route('/purchases/delete/<int:id>', methods=['POST'])
def delete_purchase(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM purchases WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM purchases WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('purchases'))

# --- ORDERS / POS MODULE ---
@app.route('/orders')
def orders():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM orders ORDER BY id DESC;")
        orders_list = cur.fetchall()
        cur.execute("SELECT * FROM inventory WHERE quantity > 0 ORDER BY item;")
        products_list = cur.fetchall()
        cur.execute("SELECT * FROM customers ORDER BY name;")
        customers_list = cur.fetchall()
        cur.close()
    else:
        orders_list = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
        products_list = conn.execute('SELECT * FROM inventory WHERE quantity > 0 ORDER BY item').fetchall()
        customers_list = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    conn.close()
    
    return render_template('orders.html', orders=orders_list, products=products_list, customers=customers_list)

@app.route('/orders/add', methods=['POST'])
def add_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    product_id = request.form.get('product_id')
    customer_name = request.form.get('customer_name', 'Walk-in')
    qty_str = request.form.get('quantity')
    
    if product_id and qty_str:
        qty = int(qty_str)
        conn, db_type = get_db_connection()
        
        if db_type == 'pg':
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM inventory WHERE id = %s;", (product_id,))
            prod = cur.fetchone()
            
            if prod and prod['quantity'] >= qty:
                new_qty = prod['quantity'] - qty
                cur.execute("UPDATE inventory SET quantity = %s WHERE id = %s;", (new_qty, product_id))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("INSERT INTO orders (product_id, product_name, customer_name, quantity, order_date) VALUES (%s, %s, %s, %s, %s);",
                            (product_id, prod['item'], customer_name, qty, now_str))
                conn.commit()
            else:
                flash("Not enough stock available!")
            cur.close()
        else:
            prod = conn.execute('SELECT * FROM inventory WHERE id = ?', (product_id,)).fetchone()
            if prod and prod['quantity'] >= qty:
                new_qty = prod['quantity'] - qty
                conn.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (new_qty, product_id))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute('INSERT INTO orders (product_id, product_name, customer_name, quantity, order_date) VALUES (?, ?, ?, ?, ?)',
                             (product_id, prod['item'], customer_name, qty, now_str))
                conn.commit()
            else:
                flash("Not enough stock available!")
        conn.close()
        
    return redirect(url_for('orders'))

@app.route('/orders/delete/<int:id>', methods=['POST'])
def delete_order(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM orders WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('orders'))

# --- SUPPLIER MODULE ---
@app.route('/suppliers')
def suppliers():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM suppliers ORDER BY id DESC;")
        suppliers_list = cur.fetchall()
        cur.close()
    else:
        suppliers_list = conn.execute('SELECT * FROM suppliers ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('suppliers.html', suppliers=suppliers_list)

@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    contact_person = request.form.get('contact_person', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    
    if name:
        conn, db_type = get_db_connection()
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("INSERT INTO suppliers (name, contact_person, email, phone, address) VALUES (%s, %s, %s, %s, %s);", (name, contact_person, email, phone, address))
            conn.commit()
            cur.close()
        else:
            conn.execute('INSERT INTO suppliers (name, contact_person, email, phone, address) VALUES (?, ?, ?, ?, ?)', (name, contact_person, email, phone, address))
            conn.commit()
        conn.close()
        
    return redirect(url_for('suppliers'))

@app.route('/suppliers/delete/<int:id>', methods=['POST'])
def delete_supplier(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM suppliers WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM suppliers WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('suppliers'))

# --- CUSTOMER MODULE ---
@app.route('/customers')
def customers():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM customers ORDER BY id DESC;")
        customers_list = cur.fetchall()
        cur.close()
    else:
        customers_list = conn.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('customers.html', customers=customers_list)

@app.route('/customers/add', methods=['POST'])
def add_customer():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    
    if name:
        conn, db_type = get_db_connection()
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("INSERT INTO customers (name, email, phone, address) VALUES (%s, %s, %s, %s);", (name, email, phone, address))
            conn.commit()
            cur.close()
        else:
            conn.execute('INSERT INTO customers (name, email, phone, address) VALUES (?, ?, ?, ?)', (name, email, phone, address))
            conn.commit()
        conn.close()
        
    return redirect(url_for('customers'))

@app.route('/customers/delete/<int:id>', methods=['POST'])
def delete_customer(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM customers WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM customers WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('customers'))

# --- CATEGORIES MODULE ---
@app.route('/categories')
def categories():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM categories ORDER BY id DESC;")
        categories_list = cur.fetchall()
        cur.close()
    else:
        categories_list = conn.execute('SELECT * FROM categories ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('categories.html', categories=categories_list)

@app.route('/categories/add', methods=['POST'])
def add_category():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if name:
        conn, db_type = get_db_connection()
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("INSERT INTO categories (name, description) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (name, description))
            conn.commit()
            cur.close()
        else:
            conn.execute('INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)', (name, description))
            conn.commit()
        conn.close()
        
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:id>', methods=['POST'])
def delete_category(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM categories WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM categories WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('categories'))

# --- PRODUCTS MODULE ---
@app.route('/products')
def products():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    search_query = request.args.get('search', '')
    conn, db_type = get_db_connection()
    
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if search_query:
            cur.execute("SELECT * FROM inventory WHERE item ILIKE %s OR category ILIKE %s ORDER BY id;", (f'%{search_query}%', f'%{search_query}%'))
        else:
            cur.execute("SELECT * FROM inventory ORDER BY id;")
        inventory = cur.fetchall()
        cur.execute("SELECT * FROM categories ORDER BY name;")
        categories_list = cur.fetchall()
        cur.close()
    else:
        if search_query:
            inventory = conn.execute('SELECT * FROM inventory WHERE item LIKE ? OR category LIKE ?', (f'%{search_query}%', f'%{search_query}%')).fetchall()
        else:
            inventory = conn.execute('SELECT * FROM inventory').fetchall()
        categories_list = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
            
    low_stock_items = [item for item in inventory if item['quantity'] <= 5]
    conn.close()
    
    return render_template('products.html', inventory=inventory, categories=categories_list, low_stock_items=low_stock_items, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_item():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    item_name = request.form.get('item')
    qty = request.form.get('quantity')
    category = request.form.get('category', 'General')
    
    if item_name and qty:
        conn, db_type = get_db_connection()
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("INSERT INTO inventory (item, quantity, category) VALUES (%s, %s, %s);", (item_name, int(qty), category))
            conn.commit()
            cur.close()
        else:
            conn.execute('INSERT INTO inventory (item, quantity, category) VALUES (?, ?, ?)', (item_name, int(qty), category))
            conn.commit()
        conn.close()
        
    return redirect(url_for('products'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    
    if request.method == 'POST':
        item_name = request.form.get('item')
        qty = request.form.get('quantity')
        category = request.form.get('category', 'General')
        
        if db_type == 'pg':
            cur = conn.cursor()
            cur.execute("UPDATE inventory SET item = %s, quantity = %s, category = %s WHERE id = %s;", (item_name, int(qty), category, id))
            conn.commit()
            cur.close()
        else:
            conn.execute('UPDATE inventory SET item = ?, quantity = ?, category = ? WHERE id = ?', (item_name, int(qty), category, id))
            conn.commit()
        conn.close()
        return redirect(url_for('products'))
        
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM inventory WHERE id = %s;", (id,))
        item = cur.fetchone()
        cur.close()
    else:
        item = conn.execute('SELECT * FROM inventory WHERE id = ?', (id,)).fetchone()
        
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_item(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM inventory WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('products'))

@app.route('/export/csv')
def export_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn, db_type = get_db_connection()
    if db_type == 'pg':
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, item, category, quantity FROM inventory ORDER BY id;")
        inventory = cur.fetchall()
        cur.close()
    else:
        inventory = conn.execute('SELECT id, item, category, quantity FROM inventory').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Item Name', 'Category', 'Quantity'])
    
    for row in inventory:
        writer.writerow([row['id'], row['item'], row['category'], row['quantity']])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=inventory_report.csv'}
    )

if __name__ == '__main__':
    app.run(debug=True)
