import requests
import sqlite3
import time
import sys

# Configuration
URL = "http://127.0.0.1:5000"
DB_PATH = "database_files/database.db"

def print_result(test_name, passed, detail):
    if passed:
        print(f"✅ [SECURE] {test_name}: {detail}")
    else:
        print(f"❌ [VULNERABLE] {test_name}: {detail}")

print("\n--- 🛡️ AUTOMATED SECURITY SCANNER RUNNING 🛡️ ---\n")

# --- TEST 1: SQL INJECTION ---
try:
    # Attempt to login using a common SQL bypass trick
    payload = {"username": "admin' OR '1'='1", "password": "x"}
    response = requests.post(f"{URL}/", data=payload)
    
    # If we see "feedback" or "success", the bypass worked (BAD)
    if "feedback" in response.text.lower() or "welcome" in response.text.lower():
        print_result("SQL Injection", False, "Login bypassed using 'OR 1=1'")
    else:
        print_result("SQL Injection", True, "Payload failed to bypass login")
except Exception as e:
    print(f"⚠️ Error testing SQLi: {e}")

# --- TEST 2: REFLECTED XSS ---
try:
    # Inject a harmless script tag
    xss_payload = "<script>alert('Test')</script>"
    response = requests.get(f"{URL}/?msg={xss_payload}")
    
    # If the tag comes back exactly as sent, it's vulnerable (BAD)
    if xss_payload in response.text:
        print_result("Reflected XSS", False, "Raw script tag returned in HTML")
    else:
        print_result("Reflected XSS", True, "Input was sanitized/escaped")
except Exception as e:
    print(f"⚠️ Error testing XSS: {e}")

# --- TEST 3: PASSWORD STORAGE ---
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password FROM users LIMIT 1")
    password = cur.fetchone()[0]
    conn.close()

    # Hashed passwords (bcrypt) usually start with $2b$ and are long
    if len(password) < 20 or not password.startswith("$"):
        print_result("Password Storage", False, f"Plain text found: '{password}'")
    else:
        print_result("Password Storage", True, "Password appears to be hashed")
except Exception as e:
    print(f"⚠️ Error reading DB: {e}")

# --- TEST 4: TIMING ATTACK ---
try:
    def measure(u):
        s = time.perf_counter()
        requests.post(f"{URL}/", data={"username": u, "password": "x"})
        return time.perf_counter() - s

    t_valid = sum([measure("admin") for _ in range(3)]) / 3
    t_invalid = sum([measure("ghost") for _ in range(3)]) / 3
    
    diff = t_valid - t_invalid
    
    if diff > 0.05: # Threshold for "significant" delay
        print_result("Timing Attack", False, f"Valid user took {diff:.4f}s longer")
    else:
        print_result("Timing Attack", True, f"Times consistent (Diff: {diff:.4f}s)")
except Exception as e:
    print(f"⚠️ Error testing Timing: {e}")

print("\n--- 🏁 SCAN COMPLETE 🏁 ---")

