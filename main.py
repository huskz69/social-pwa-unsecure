import os
import sys
import sqlite3
import subprocess
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, session, abort
from flask_cors import CORS
import user_management as db
import secrets
 
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, "database_files", "database.db")
SETUP_SCRIPT = os.path.join(BASE_DIR, "database_files", "setup_db.py")
ALLOWED_HOST = os.environ.get("ALLOWED_HOST", "127.0.0.1:5000")
 
 
def _tables_exist():
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
 
app = Flask(__name__)
 
CORS(app, origins=[f"http://{ALLOWED_HOST}", f"https://{ALLOWED_HOST}"])
 
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
 
 
def _safe_redirect(url):
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != ALLOWED_HOST:
        return None
    return url
 
 
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
            session["username"] = username
            posts = db.getPosts()
            return render_template("feed.html", username=username, state=isLoggedIn, posts=posts)
        else:
            return render_template("index.html", msg="Invalid credentials. Please try again.")
 
 
@app.route("/signup.html", methods=["POST", "GET"])
def signup():
    if request.method == "GET" and request.args.get("url"):
        target = _safe_redirect(request.args.get("url"))
        if target:
            return redirect(target, code=302)
        abort(400)
 
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        DoB      = request.form["dob"]
        bio      = request.form.get("bio", "")
 
        if not username or len(password) < 8:
            return render_template("signup.html", msg="Username required and password must be at least 8 characters.")
 
        existing = db.getUserProfile(username)
        if existing:
            return render_template("signup.html", msg="Username already taken.")
 
        db.insertUser(username, password, DoB, bio)
        return render_template("index.html", msg="Account created! Please log in.")
    else:
        return render_template("signup.html")
 
 
@app.route("/feed.html", methods=["POST", "GET"])
def feed():
    if request.method == "GET" and request.args.get("url"):
        target = _safe_redirect(request.args.get("url"))
        if target:
            return redirect(target, code=302)
        abort(400)
 
    if "username" not in session:
        return redirect("/")
 
    if request.method == "POST":
        post_content = request.form["content"]
        username = session["username"]
        db.insertPost(username, post_content)
        posts = db.getPosts()
        return render_template("feed.html", username=username, state=True, posts=posts)
    else:
        posts = db.getPosts()
        username = session["username"]
        return render_template("feed.html", username=username, state=True, posts=posts)
 
 
@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect("/")
 
    username = request.args.get("user", "")
    profile_data = db.getUserProfile(username)
    return render_template("profile.html", profile=profile_data, username=username)
 
 
@app.route("/messages", methods=["POST", "GET"])
def messages():
    if "username" not in session:
        return redirect("/")
 
    sender = session["username"]
    if request.method == "POST":
        recipient = request.form.get("recipient", "")
        body      = request.form.get("body", "")
        db.sendMessage(sender, recipient, body)
        msgs = db.getMessages(recipient)
        return render_template("messages.html", messages=msgs, username=sender, recipient=recipient)
    else:
        msgs = db.getMessages(sender)
        return render_template("messages.html", messages=msgs, username=sender, recipient=sender)
 
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
 
 
@app.route("/success.html")
def success():
    msg = request.args.get("msg", "Your action was completed successfully.")
    return render_template("success.html", msg=msg)
 
 
if __name__ == "__main__":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)
 