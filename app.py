from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
import csv
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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
    user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not user:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', 'password123'))
    conn.commit()
    conn.close()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid Username or Password!')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    
    if search_query:
        inventory = conn.execute(
            'SELECT * FROM inventory WHERE item LIKE ? OR category LIKE ?', 
            (f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        inventory = conn.execute('SELECT * FROM inventory').fetchall()
        
    low_stock_items = [item for item in inventory if item['quantity'] <= 5]
    conn.close()
    
    return render_template('index.html', inventory=inventory, low_stock_items=low_stock_items, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_item():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    item_name = request.form.get('item')
    qty = request.form.get('quantity')
    category = request.form.get('category', 'General')
    
    if item_name and qty:
        conn = get_db_connection()
        conn.execute('INSERT INTO inventory (item, quantity, category) VALUES (?, ?, ?)', (item_name, int(qty), category))
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        item_name = request.form.get('item')
        qty = request.form.get('quantity')
        category = request.form.get('category', 'General')
        
        conn.execute('UPDATE inventory SET item = ?, quantity = ?, category = ? WHERE id = ?', (item_name, int(qty), category, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
        
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_item(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM inventory WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/export/csv')
def export_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = get_db_connection()
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
