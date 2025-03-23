import sqlite3
from config import DATABASE_PATH

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            shop_name TEXT,
            contact TEXT,
            role TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_sender TEXT,
            phone_receiver TEXT,
            pickup_address TEXT,
            delivery_address TEXT,
            distance REAL,
            total_cost REAL,
            photo_file_id TEXT,
            media_type TEXT,
            description TEXT,
            weight TEXT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, shop_name, contact, role="store"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, shop_name, contact, role)
        VALUES (?, ?, ?, ?)
    ''', (user_id, shop_name, contact, role))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_order(user_id, phone_sender, phone_receiver, pickup_address, delivery_address,
              distance, total_cost, photo_file_id, media_type, description, weight):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, phone_sender, phone_receiver, pickup_address, delivery_address, 
                            distance, total_cost, photo_file_id, media_type, description, weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, phone_sender, phone_receiver, pickup_address, delivery_address,
          distance, total_cost, photo_file_id, media_type, description, weight))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

def get_orders_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id")
    users = cursor.fetchall()
    conn.close()
    return users

def get_all_orders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY order_date")
    orders = cursor.fetchall()
    conn.close()
    return orders
