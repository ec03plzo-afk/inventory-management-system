from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

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
            quantity INTEGER NOT NULL
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
        
    conn = get_db_connection()
    inventory = conn.execute('SELECT * FROM inventory').fetchall()
    conn.close()
    return render_template('index.html', inventory=inventory)

@app.route('/add', methods=['POST'])
def add_item():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    item_name = request.form.get('item')
    qty = request.form.get('quantity')
    
    if item_name and qty:
        conn = get_db_connection()
        conn.execute('INSERT INTO inventory (item, quantity) VALUES (?, ?)', (item_name, int(qty)))
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
        
        conn.execute('UPDATE inventory SET item = ?, quantity = ? WHERE id = ?', (item_name, int(qty), id))
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

if __name__ == '__main__':
    app.run(debug=True)
