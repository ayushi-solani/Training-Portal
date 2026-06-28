"""
Training Portal — app.py
"""
import os, smtplib
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "training_portal_secret_2024"

# ── DATABASE CONFIG (edit as needed) ──────────────────────────
DB_CONFIG = {
    "host":        "localhost",
    "user":        "root",
    "password":    "root",
    "database":    "training_portal",
    "autocommit":  False,
}

# ── EMAIL CONFIG (optional — set to enable forwarding) ────────
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = ""          # your gmail
SMTP_PASSWORD = ""          # app password
EMAIL_ENABLED = False       # set True after configuring above

# ── DB HELPERS ────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db and db.is_connected():
        db.close()

def query(sql, args=(), one=False):
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(sql, args)
    rv  = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return rv

def execute(sql, args=()):
    db  = get_db()
    cur = db.cursor()
    cur.execute(sql, args)
    db.commit()
    lid = cur.lastrowid
    cur.close()
    return lid

# ── STATUS HELPER ─────────────────────────────────────────────
def training_status(t, employee_id=None):
    today = date.today()
    reg_open  = t["reg_open_date"]
    reg_close = t["reg_close_date"]
    start     = t["start_date"]
    end       = t["end_date"]

    if today < reg_open:
        return "Upcoming"
    elif reg_open <= today <= reg_close:
        return "Registration"
    elif reg_close < today <= end:
        return "Ongoing"
    else:
        # after end_date
        if employee_id:
            fb = query("SELECT id FROM feedback WHERE training_id=%s AND employee_id=%s",
                       (t["id"], employee_id), one=True)
            return "Finished" if fb else "Need Feedback"
        return "Need Feedback"

# ── AUTH HELPERS ──────────────────────────────────────────────
def login_required(role=None):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}_dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        pwd   = request.form["password"]
        user  = query("SELECT * FROM users WHERE email=%s AND is_active=1", (email,), one=True)
        if user and check_password_hash(user["password_hash"], pwd):
            session["user_id"]   = user["id"]
            session["user_name"] = user["full_name"]
            session["role"]      = user["role"]
            session["dept"]      = user["department"]
            return redirect(url_for(f"{user['role']}_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        full_name  = request.form["full_name"].strip()
        email      = request.form["email"].strip()
        pwd        = request.form["password"]
        department = request.form["department"].strip()
        existing   = query("SELECT id FROM users WHERE email=%s", (email,), one=True)
        if existing:
            flash("Email already registered.", "danger")
        else:
            execute("INSERT INTO users (full_name, email, password_hash, role, department) VALUES (%s,%s,%s,'employee',%s)",
                    (full_name, email, generate_password_hash(pwd), department))
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ══════════════════════════════════════════════════════════════
#  EMPLOYEE ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/employee/dashboard")
@login_required(role="employee")
def employee_dashboard():
    uid = session["user_id"]
    my_regs = query("""
        SELECT t.*, r.registered_at FROM trainings t
        JOIN registrations r ON t.id = r.training_id
        WHERE r.employee_id = %s AND t.is_active = 1
        ORDER BY t.start_date DESC LIMIT 5
    """, (uid,))
    for t in my_regs:
        t["status"] = training_status(t, uid)

    stats = {
        "total":       query("SELECT COUNT(*) as c FROM registrations WHERE employee_id=%s", (uid,), one=True)["c"],
        "ongoing":     0,
        "need_fb":     0,
        "finished":    0,
    }
    all_regs = query("""
        SELECT t.* FROM trainings t
        JOIN registrations r ON t.id=r.training_id
        WHERE r.employee_id=%s AND t.is_active=1
    """, (uid,))
    for t in all_regs:
        s = training_status(t, uid)
        if s == "Ongoing":         stats["ongoing"] += 1
        elif s == "Need Feedback": stats["need_fb"] += 1
        elif s == "Finished":      stats["finished"] += 1

    return render_template("employee/dashboard.html", my_regs=my_regs, stats=stats)

@app.route("/employee/browse")
@login_required(role="employee")
def employee_browse():
    uid = session["user_id"]
    search = request.args.get("q","")
    dept   = request.args.get("dept","")

    sql = "SELECT * FROM trainings WHERE is_active=1"
    args = []
    if search:
        sql += " AND (title LIKE %s OR topic LIKE %s)"
        args += [f"%{search}%", f"%{search}%"]
    if dept:
        sql += " AND department = %s"
        args.append(dept)
    sql += " ORDER BY reg_open_date DESC"

    trainings = query(sql, args)
    registered_ids = {r["training_id"] for r in
                      query("SELECT training_id FROM registrations WHERE employee_id=%s", (uid,))}
    departments = [r["department"] for r in
                   query("SELECT DISTINCT department FROM trainings WHERE is_active=1 AND department IS NOT NULL")]

    for t in trainings:
        t["status"]      = training_status(t)
        t["is_registered"] = t["id"] in registered_ids
        t["seats_left"]  = t["max_seats"] - (
            query("SELECT COUNT(*) as c FROM registrations WHERE training_id=%s", (t["id"],), one=True)["c"])

    return render_template("employee/browse.html", trainings=trainings,
                           departments=departments, search=search, selected_dept=dept)

@app.route("/employee/register/<int:tid>", methods=["POST"])
@login_required(role="employee")
def employee_register(tid):
    uid = session["user_id"]
    t   = query("SELECT * FROM trainings WHERE id=%s AND is_active=1", (tid,), one=True)
    if not t:
        flash("Training not found.", "danger")
        return redirect(url_for("employee_browse"))
    if training_status(t) != "Registration":
        flash("Registration is not open for this training.", "warning")
        return redirect(url_for("employee_browse"))
    existing = query("SELECT id FROM registrations WHERE training_id=%s AND employee_id=%s", (tid, uid), one=True)
    if existing:
        flash("You are already registered.", "warning")
    else:
        execute("INSERT INTO registrations (training_id, employee_id) VALUES (%s,%s)", (tid, uid))
        flash("Successfully registered!", "success")
    return redirect(url_for("employee_browse"))

@app.route("/employee/my-trainings")
@login_required(role="employee")
def employee_my_trainings():
    uid = session["user_id"]
    regs = query("""
        SELECT t.*, r.registered_at FROM trainings t
        JOIN registrations r ON t.id = r.training_id
        WHERE r.employee_id = %s AND t.is_active = 1
        ORDER BY t.start_date DESC
    """, (uid,))
    for t in regs:
        t["status"] = training_status(t, uid)
    return render_template("employee/my_training.html", regs=regs)

@app.route("/employee/request", methods=["GET","POST"])
@login_required(role="employee")
def employee_request():
    uid = session["user_id"]
    if request.method == "POST":
        topic  = request.form["topic"].strip()
        reason = request.form.get("reason","").strip()
        execute("INSERT INTO employee_requests (employee_id, topic, reason) VALUES (%s,%s,%s)",
                (uid, topic, reason))
        flash("Training request submitted!", "success")
        return redirect(url_for("employee_my_trainings"))
    my_requests = query("SELECT * FROM employee_requests WHERE employee_id=%s ORDER BY created_at DESC", (uid,))
    return render_template("employee/request_training.html", my_requests=my_requests)

@app.route("/employee/feedback/<int:tid>", methods=["GET","POST"])
@login_required(role="employee")
def employee_feedback(tid):
    uid = session["user_id"]
    t   = query("SELECT * FROM trainings WHERE id=%s", (tid,), one=True)
    if not t:
        flash("Training not found.", "danger")
        return redirect(url_for("employee_my_trainings"))
    existing_fb = query("SELECT * FROM feedback WHERE training_id=%s AND employee_id=%s", (tid, uid), one=True)

    if request.method == "POST":
        if existing_fb:
            flash("Feedback already submitted.", "warning")
            return redirect(url_for("employee_my_trainings"))
        rating   = int(request.form["rating"])
        comments = request.form.get("comments","").strip()
        execute("INSERT INTO feedback (training_id, employee_id, rating, comments) VALUES (%s,%s,%s,%s)",
                (tid, uid, rating, comments))
        flash("Feedback submitted. Thank you!", "success")
        return redirect(url_for("employee_my_trainings"))
    return render_template("employee/feedback.html", training=t, existing_fb=existing_fb)

# ══════════════════════════════════════════════════════════════
#  HR ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/hr/dashboard")
@login_required(role="hr")
def hr_dashboard():
    stats = {
        "total_trainings": query("SELECT COUNT(*) as c FROM trainings WHERE is_active=1", one=True)["c"],
        "total_employees": query("SELECT COUNT(*) as c FROM users WHERE role='employee' AND is_active=1", one=True)["c"],
        "pending_requests": query("SELECT COUNT(*) as c FROM employee_requests WHERE status='pending'", one=True)["c"],
        "total_regs": query("SELECT COUNT(*) as c FROM registrations", one=True)["c"],
    }
    recent = query("SELECT * FROM trainings WHERE is_active=1 ORDER BY created_at DESC LIMIT 5")
    for t in recent:
        t["status"] = training_status(t)
        t["reg_count"] = query("SELECT COUNT(*) as c FROM registrations WHERE training_id=%s", (t["id"],), one=True)["c"]
    return render_template("hr/dashboard.html", stats=stats, recent=recent)

@app.route("/hr/trainings")
@login_required(role="hr")
def hr_trainings():
    trainings = query("SELECT * FROM trainings WHERE is_active=1 ORDER BY created_at DESC")
    for t in trainings:
        t["status"]    = training_status(t)
        t["reg_count"] = query("SELECT COUNT(*) as c FROM registrations WHERE training_id=%s", (t["id"],), one=True)["c"]
    return render_template("hr/manage_training.html", trainings=trainings)

@app.route("/hr/trainings/create", methods=["GET","POST"])
@login_required(role="hr")
def hr_create_training():
    if request.method == "POST":
        execute("""
            INSERT INTO trainings
              (title, description, topic, department, trainer_name,
               reg_open_date, reg_close_date, start_date, end_date, max_seats, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form["title"], request.form.get("description",""),
            request.form.get("topic",""), request.form.get("department",""),
            request.form.get("trainer_name",""),
            request.form["reg_open_date"], request.form["reg_close_date"],
            request.form["start_date"], request.form["end_date"],
            int(request.form.get("max_seats", 50)),
            session["user_id"]
        ))
        flash("Training created successfully!", "success")
        return redirect(url_for("hr_trainings"))
    return render_template("hr/create_training.html")

@app.route("/hr/requests")
@login_required(role="hr")
def hr_requests():
    requests_list = query("""
        SELECT er.*, u.full_name, u.department FROM employee_requests er
        JOIN users u ON er.employee_id = u.id
        ORDER BY er.created_at DESC
    """)
    return render_template("hr/requests.html", requests=requests_list)

@app.route("/hr/requests/<int:rid>/approve", methods=["POST"])
@login_required(role="hr")
def hr_approve_request(rid):
    req = query("SELECT * FROM employee_requests WHERE id=%s", (rid,), one=True)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for("hr_requests"))

    tid = execute("""
        INSERT INTO trainings
          (title, topic, department, reg_open_date, reg_close_date,
           start_date, end_date, max_seats, created_by, source, request_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'employee_request',%s)
    """, (
        request.form["title"], req["topic"],
        request.form.get("department",""),
        request.form["reg_open_date"], request.form["reg_close_date"],
        request.form["start_date"], request.form["end_date"],
        int(request.form.get("max_seats", 50)),
        session["user_id"], rid
    ))
    execute("UPDATE employee_requests SET status='approved', training_id=%s, hr_remarks=%s WHERE id=%s",
            (tid, request.form.get("remarks",""), rid))
    flash("Request approved and training listed!", "success")
    return redirect(url_for("hr_requests"))

@app.route("/hr/requests/<int:rid>/reject", methods=["POST"])
@login_required(role="hr")
def hr_reject_request(rid):
    remarks = request.form.get("remarks","")
    execute("UPDATE employee_requests SET status='rejected', hr_remarks=%s WHERE id=%s", (remarks, rid))
    flash("Request rejected.", "info")
    return redirect(url_for("hr_requests"))

@app.route("/hr/trainings/<int:tid>/registrations")
@login_required(role="hr")
def hr_registrations(tid):
    t    = query("SELECT * FROM trainings WHERE id=%s", (tid,), one=True)
    regs = query("""
        SELECT u.full_name, u.email, u.department, r.registered_at
        FROM registrations r JOIN users u ON r.employee_id = u.id
        WHERE r.training_id = %s ORDER BY r.registered_at
    """, (tid,))
    return render_template("hr/registrations.html", training=t, regs=regs)

@app.route("/hr/trainings/<int:tid>/forward", methods=["POST"])
@login_required(role="hr")
def hr_forward(tid):
    if not EMAIL_ENABLED:
        flash("Email not configured. Set SMTP_USER and SMTP_PASSWORD in app.py.", "warning")
        return redirect(url_for("hr_registrations", tid=tid))

    t    = query("SELECT * FROM trainings WHERE id=%s", (tid,), one=True)
    regs = query("""
        SELECT u.full_name, u.email, u.department FROM registrations r
        JOIN users u ON r.employee_id = u.id WHERE r.training_id=%s
    """, (tid,))
    to_email = request.form.get("to_email","").strip()
    if not to_email:
        flash("Please enter the recipient email.", "warning")
        return redirect(url_for("hr_registrations", tid=tid))

    rows = "\n".join([f"  - {r['full_name']} ({r['department']}) — {r['email']}" for r in regs])
    body = (f"Dear Department,\n\nPlease find the list of employees registered for the training:\n\n"
            f"Training : {t['title']}\n"
            f"Topic    : {t['topic']}\n"
            f"Dates    : {t['start_date']} to {t['end_date']}\n\n"
            f"Registered Employees:\n{rows}\n\n"
            f"Regards,\nHR — DRDO Training Portal")

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = to_email
    msg["Subject"] = f"Employee List — {t['title']} ({t['start_date']} to {t['end_date']})"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        flash(f"Employee list forwarded to {to_email}!", "success")
    except Exception as e:
        flash(f"Email failed: {e}", "danger")

    return redirect(url_for("hr_registrations", tid=tid))

if __name__ == "__main__":
    app.run(debug=True)