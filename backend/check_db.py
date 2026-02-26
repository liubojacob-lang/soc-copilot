import sqlite3
conn = sqlite3.connect('../data/app.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [r[0] for r in cursor.fetchall()])
try:
    cursor.execute("SELECT * FROM alembic_version")
    print('Alembic version:', cursor.fetchone())
except:
    print('No alembic_version table')
conn.close()
