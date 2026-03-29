import os
import sys
import sqlite3
import subprocess
from flask import Flask, render_template, request, redirect
from flask_cors import CORS
import user_management as db
import secrets


# ── Auto-bootstrap the database on every startup ──────────────────────────────
# This ensures students never see "no such table" even if setup_db.py
# was never manually run, or if the .db file is missing / corrupted.
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, "database_files", "database.db")
SETUP_SCRIPT = os.path.join(BASE_DIR, "database_files", "setup_db.py")

def _tables_exist():
    """Return True if the required tables are all present."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        con.close()
        return {"users", "posts", "messages"}.issubset(tables)
    except Exception:
        return False

def init_db():
    os.makedirs(os.path.join(BASE_DIR, "database_files"), exist_ok=True)
    if not os.path.exists(DB_PATH) or not _tables_exist():
        print("[SocialPWA] Setting up database...")
        result = subprocess.run(
            [sys.executable, SETUP_SCRIPT],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print("[SocialPWA] WARNING: setup_db failed:", result.stderr)
    else:
        print("[SocialPWA] Database already exists — skipping setup.")

init_db()

# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

# VULNERABILITY: Wildcard CORS — allows ANY origin to make credentialed requests
CORS(app)

app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

def _safe_redirect(url):
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != ALLOWED_HOST:
        return None
    return url

# ── Home / Login ──────────────────────────────────────────────────────────────

@app.route("/", methods=["POST", "GET"])
@app.route("/index.html", methods=["POST", "GET"])
def home():
    if request.method == "GET" and request.args.get("url"):
        target = _safe_redirect(request.args.get("url"))
        if target:
            return redirect(target, code=302)
        abort(400)
    if request.method == "GET":
        msg = request.args.get("msg", "")
        return render_template("index.html", msg=msg)
    
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        isLoggedIn = db.retrieveUsers(username, password)
        if isLoggedIn:
            posts = db.getPosts()
            return render_template("feed.html", username=username, state=isLoggedIn, posts=posts)
        else:
            return render_template("index.html", msg="Invalid credentials. Please try again.")


# ── Sign Up ───────────────────────────────────────────────────────────────────

@app.route("/signup.html", methods=["POST", "GET"])
def signup():
    if request.method == "GET" and request.args.get("url"):
        return redirect(request.args.get("url"), code=302)

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        DoB      = request.form["dob"]
        bio      = request.form.get("bio", "")
        # VULNERABILITY: No duplicate username check
        # VULNERABILITY: No input validation or password strength enforcement
        db.insertUser(username, password, DoB, bio)
        return render_template("index.html", msg="Account created! Please log in.")
    else:
        return render_template("signup.html")


# ── Social Feed ───────────────────────────────────────────────────────────────

@app.route("/feed.html", methods=["POST", "GET"])
def feed():
    if request.method == "GET" and request.args.get("url"):
        return redirect(request.args.get("url"), code=302)

    if request.method == "POST":
        post_content = request.form["content"]
        # VULNERABILITY: IDOR — username from hidden form field, can be tampered with
        username = request.form.get("username", "Anonymous")
        db.insertPost(username, post_content)
        posts = db.getPosts()
        return render_template("feed.html", username=username, state=True, posts=posts)
    else:
        posts = db.getPosts()
        return render_template("feed.html", username="Guest", state=True, posts=posts)


# ── User Profile ──────────────────────────────────────────────────────────────

@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect("/login")
        
    username = request.args.get("user", "")
    profile_data = db.getUserProfile(username)
    return render_template("profile.html", profile=profile_data, username=username)

# ── Direct Messages ───────────────────────────────────────────────────────────

@app.route("/messages", methods=["POST", "GET"])
def messages():
    # VULNERABILITY: No authentication — change ?user= to read anyone's inbox
    if request.method == "POST":
        sender    = request.form.get("sender", "Anonymous")
        recipient = request.form.get("recipient", "")
        body      = request.form.get("body", "")
        db.sendMessage(sender, recipient, body)
        msgs = db.getMessages(recipient)
        return render_template("messages.html", messages=msgs, username=sender, recipient=recipient)
    else:
        username = request.args.get("user", "Guest")
        msgs = db.getMessages(username)
        return render_template("messages.html", messages=msgs, username=username, recipient=username)


# ── Success Page ──────────────────────────────────────────────────────────────

@app.route("/success.html")
def success():
    msg = request.args.get("msg", "Your action was completed successfully.")
    return render_template("success.html", msg=msg)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.run(debug=True, host="0.0.0.0", port=5000)
