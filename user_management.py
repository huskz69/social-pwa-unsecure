import sqlite3 as sql
import time
import random
import os

# ─────────────────────────────────────────────────────────────────────────────
#  user_management.py
#  Handles all direct database operations for the Unsecure Social PWA.
#
#  INTENTIONAL VULNERABILITIES (for educational use):
#    1. SQL Injection      — f-string queries throughout
#    2. Plaintext passwords — no hashing applied at any point
#    3. Timing side-channel — sleep only fires when username EXISTS
#    4. No input validation — any string accepted as username/password
#    5. IDOR-equivalent    — username passed from client-side hidden field
# ─────────────────────────────────────────────────────────────────────────────

# Absolute paths — works regardless of where `python main.py` is called from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "database_files", "database.db")
LOG_PATH = os.path.join(BASE_DIR, "visitor_log.txt")


def insertUser(username, password, DoB, bio=""):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    con = sql.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO users (username, password, dateOfBirth, bio) VALUES (?,?,?,?)",
        (username, password, DoB, bio),
    )
    con.commit()
    con.close()


def retrieveUsers(username, password):
    con = sql.connect(DB_PATH)
    cur = con.cursor()

    time.sleep(random.randint(80, 90) / 1000)


    cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    result = cur.fetchone()

    if row is None:
        con.close()
        return False

    try:
        with open(LOG_PATH, "r") as f:
            count = int(f.read().strip() or 0)
        with open(LOG_PATH, "w") as f:
            f.write(str(count + 1))
    except Exception:
        pass

    con.close()
    return True

def insertPost(author, content):
    """
    Insert a post.
    VULNERABILITY: SQL Injection via f-string on both author and content.
    VULNERABILITY: author comes from a hidden HTML field — easily spoofed (IDOR).
    """
    con = sql.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(f"INSERT INTO posts (author, content) VALUES ('{author}', '{content}')")
    con.commit()
    con.close()


def getPosts():
    """
    Get all posts newest-first.
    NOTE: Content returned here is rendered with |safe in feed.html — stored XSS.
    """
    con = sql.connect(DB_PATH)
    cur = con.cursor()
    data = cur.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    con.close()
    return data


def getUserProfile(username):

    con = sql.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, username, dateOfBirth, bio, role FROM users WHERE username = ?",(username,))    
    row = cur.fetchone()
    con.close()
    return row


def getMessages(username):
    """
    Get inbox for a user.
    VULNERABILITY: SQL Injection via f-string.
    VULNERABILITY: No auth check — change ?user= to read anyone's inbox.
    """
    con = sql.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(f"SELECT * FROM messages WHERE recipient = '{username}' ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows


def sendMessage(sender, recipient, body):
    """
    Send a DM.
    VULNERABILITY: SQL Injection on all three fields.
    VULNERABILITY: sender taken from hidden form field — can be spoofed.
    """
    con = sql.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(f"INSERT INTO messages (sender, recipient, body) VALUES ('{sender}', '{recipient}', '{body}')")
    con.commit()
    con.close()


def getVisitorCount():
    """Return login attempt count."""
    try:
        with open(LOG_PATH, "r") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0
