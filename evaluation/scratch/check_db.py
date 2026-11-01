import sqlite3
conn = sqlite3.connect('backend/sql_app.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
print('backend/sql_app.db users columns:', cols)
cur.execute('SELECT id, email FROM users LIMIT 5')
print('rows:', cur.fetchall())
conn.close()

