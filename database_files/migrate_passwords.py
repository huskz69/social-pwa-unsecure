import sqlite3
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database_files", "database.db")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

cur.execute("SELECT id, password FROM users")
rows = cur.fetchall()

for user_id, password in rows:
    if not password.startswith("$2b$"):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        print(f"Rehashed user id={user_id}")

con.commit()
con.close()
print("Done.")