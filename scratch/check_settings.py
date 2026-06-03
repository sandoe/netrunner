import sqlite3
conn = sqlite3.connect('data/netrunner.db')
cursor = conn.cursor()
cursor.execute("SELECT key, value FROM settings")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")
conn.close()
