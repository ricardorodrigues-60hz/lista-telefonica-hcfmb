import sqlite3
conn = sqlite3.connect('lista.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print('Tabelas no banco:', [t[0] for t in tables])
conn.close()
