import sqlite3
import os

DATABASE = os.path.join('instance', 'orders.db')
os.makedirs('instance', exist_ok=True)

conn = sqlite3.connect(DATABASE)
conn.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    style TEXT,
    size TEXT,
    paper_type TEXT,
    deadline TEXT,
    paper_count INTEGER,
    text_content TEXT,
    word_count INTEGER,
    amount REAL,
    created_at TEXT
)
''')
conn.commit()
conn.close()
print(f"Database initialized at {DATABASE}")