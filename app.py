from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
import os
import csv
import io

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
                password VARCHAR(255) NOT NULL
            );
        ''')
        cur.execute("SELECT * FROM users WHERE username = %s;", ('admin@gmail.com',))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", ('admin@gmail.com', 'password123'))
        conn.commit()
        cur.close()
    else:
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
                password TEXT NOT NULL
            )
        ''')
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin@gmail.com',)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin@gmail.com', 'password123'))
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
        cur.close()
    else:
        inventory = conn.execute('SELECT * FROM inventory').fetchall()
        categories_list = conn.execute('SELECT * FROM categories').fetchall()
        
    total_products = len(inventory)
    total_categories = len(categories_list)
    conn.close()
    
    return render_template('dashboard.html', total_products=total_products, total_categories=total_categories)

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

@app.route('/section/<title>')
def view_section(title):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('section.html', title=title)

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
