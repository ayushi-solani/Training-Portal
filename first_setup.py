"""
Training Portal — first_setup.py
Run once to create DB, tables, and demo accounts.
"""
import sys, os, re
import mysql.connector
from werkzeug.security import generate_password_hash

# ── helpers ──────────────────────────────────────────────────
def step(n, msg): print(f"[{n}] {msg}")
def ok(msg):      print(f"    ✓ {msg}")
def warn(msg):    print(f"    ⚠ {msg}")
def fail(msg):    print(f"    ✗ {msg}"); sys.exit(1)

# ── 1. python version ─────────────────────────────────────────
step(1, "Checking Python version…")
if sys.version_info < (3, 8):
    fail("Python 3.8+ required.")
ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# ── 2. dependencies ───────────────────────────────────────────
step(2, "Installing dependencies…")
os.system("pip install flask mysql-connector-python werkzeug --quiet")
ok("All dependencies installed.")

# ── 3. credentials ────────────────────────────────────────────
step(3, "MySQL credentials")
print("    Enter your MySQL connection details.")
host     = input("    Host     [localhost]: ").strip() or "localhost"
user     = input("    User     [root]: ").strip() or "root"
password = input("    Password (hidden): ").strip()
db_name  = input("    Database [training_portal]: ").strip() or "training_portal"

# ── 4. create database ────────────────────────────────────────
step(4, f"Creating database '{db_name}'…")
try:
    conn = mysql.connector.connect(host=host, user=user, password=password)
    cur  = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    ok(f"Database '{db_name}' ready.")
except mysql.connector.Error as e:
    fail(f"Cannot connect to MySQL: {e}")

# ── 5. run schema ─────────────────────────────────────────────
step(5, "Running schema.sql…")
cur.execute(f"USE `{db_name}`")

schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
if not os.path.exists(schema_path):
    fail("schema.sql not found.")

with open(schema_path, "r", encoding="utf-8") as f:
    sql_raw = f.read()

sql_cleaned  = re.sub(r'--[^\n]*', '', sql_raw)
sql_cleaned  = re.sub(r'/\*.*?\*/', '', sql_cleaned, flags=re.DOTALL)
statements   = [s.strip() for s in sql_cleaned.split(";") if s.strip()]

for stmt in statements:
    try:
        cur.execute(stmt)
        conn.commit()
    except mysql.connector.Error as e:
        if e.errno in (1050, 1062):   # table exists / duplicate entry
            continue
        warn(f"SQL warning ({e.errno}): {e.msg}")

ok("Schema applied.")

# ── 6. demo accounts ──────────────────────────────────────────
step(6, "Creating demo accounts…")

demo_users = [
    ("HR Admin",      "hr@drdo.in",     "Hr@1234",      "hr",       "Human Resources"),
    ("Ayushi Solani", "ayushi@drdo.in", "Ayushi@1234",  "employee", "Electronics & Radar"),
    ("Raj Sharma",    "raj@drdo.in",    "Raj@1234",     "employee", "Computer Science"),
    ("Priya Mehta",   "priya@drdo.in",  "Priya@1234",   "employee", "Biochemistry"),
]

for full_name, email, pwd, role, dept in demo_users:
    hashed = generate_password_hash(pwd)
    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            cur.execute("""UPDATE users SET password_hash=%s, full_name=%s, role=%s, department=%s WHERE email=%s""",
                        (hashed, full_name, role, dept, email))
        else:
            cur.execute("""INSERT INTO users (full_name, email, password_hash, role, department)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (full_name, email, hashed, role, dept))
        conn.commit()
        ok(f"{'Updated' if existing else 'Created'}  {email:<35} ({role})  →  password: {pwd}")
    except mysql.connector.Error as e:
        warn(f"Could not upsert {email}: {e}")

# ── 7. patch app.py ───────────────────────────────────────────
step(7, "Patching app.py with DB credentials…")
app_path = os.path.join(os.path.dirname(__file__), "app.py")
if os.path.exists(app_path):
    with open(app_path, "r", encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r'("host"\s*:\s*)["\'].*?["\']',     f'\\1"{host}"',     src)
    src = re.sub(r'("user"\s*:\s*)["\'].*?["\']',     f'\\1"{user}"',     src)
    src = re.sub(r'("password"\s*:\s*)["\'].*?["\']', f'\\1"{password}"', src)
    src = re.sub(r'("database"\s*:\s*)["\'].*?["\']', f'\\1"{db_name}"',  src)
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(src)
    ok("app.py updated.")
    warn("Do NOT commit app.py with a real password to Git.")
else:
    warn("app.py not found — skipping patch.")

# ── done ──────────────────────────────────────────────────────
print("""
==============================================================
  Setup Complete!
==============================================================
  Run:   python app.py
  Open:  http://localhost:5000

  Demo Credentials:
  ┌────────────┬──────────────────────┬──────────────┐
  │ Role       │ Email                │ Password     │
  ├────────────┼──────────────────────┼──────────────┤
  │ HR         │ hr@drdo.in           │ Hr@1234      │
  │ Employee   │ ayushi@drdo.in       │ Ayushi@1234  │
  │ Employee   │ raj@drdo.in          │ Raj@1234     │
  │ Employee   │ priya@drdo.in        │ Priya@1234   │
  └────────────┴──────────────────────┴──────────────┘
""")

cur.close()
conn.close()