from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
import csv
import sqlite3
from datetime import datetime, date
from reportlab.pdfgen import canvas

app = Flask(__name__)

app.secret_key = "smart_task_manager_project"

# Database Create
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tasks TEXT,
    created_at TEXT,
    user_id INTEGER
)
""")

try:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN status INTEGER DEFAULT 0"
    )
except:
    pass

try:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Medium'"

    )
except:
    pass

try:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN due_date TEXT"
    )
except:
    pass

conn.commit()
conn.close()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session ["user_id"] = user[0]
            session["username"] = user[1]
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid Email or Password"
            )

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if"@" not in email or "." not in email:
            return render_template(
                "register.html",
                error="Please enter a valid email address!"
            )

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, password)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except:
            return "Email already registered!"

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=?",
        (session["user_id"],)
    )
    total_tasks = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=? AND status=1",
        (session["user_id"],)
    )
    completed_count = cursor.fetchone()[0]

    pending_count = total_tasks - completed_count

    # All Tasks
    cursor.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    )

    all_tasks = cursor.fetchall()

    # Search Results
    search_results = []

    if search:
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id=? AND tasks LIKE ? ORDER BY id DESC",
            (session["user_id"], f"%{search}%")
        )
        search_results = cursor.fetchall()

    pending_tasks = []
    completed_tasks = []

    for task in all_tasks:
        if task[4] == 0:
            pending_tasks.append(task)
        else:
            completed_tasks.append(task)

    if search:
        tasks = search_results
    else:
        tasks = all_tasks
    
    conn.close()

    return render_template(
         "dashboard.html",
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        search_results=search_results,
        username=session.get("username"),
        search=search,
        today=date.today().strftime("%Y-%m-%d"),

        total_tasks=total_tasks,
        pending_count=pending_count,
        completed_count=completed_count
    )


@app.route("/add_task", methods=["POST"])
def add_task():

    task = request.form["task"]
    priority = request.form["priority"]
    due_date = request.form["due_date"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%d %b %Y %I:%M %p")

    user_id = session["user_id"]

    cursor.execute(
    """
    INSERT INTO tasks
    (tasks, created_at, user_id, priority, due_date) VALUES(?, ?, ?, ?, ?)
    """,
    (
        task, 
        current_time, 
        user_id, 
        priority, 
        due_date
    )
)

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/complete/<int:id>")
def complete_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM tasks WHERE id=?",
        (id,)
    )

    current_status = cursor.fetchone()[0]

    if current_status == 0:
        new_status = 1
    else:
        new_status = 0

    cursor.execute(
        "UPDATE tasks SET status=? WHERE id=?",
        (new_status, id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        updated_task = request.form["task"]

        cursor.execute(
            "UPDATE tasks SET tasks=? WHERE id=?",
            (updated_task, id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    cursor.execute(
        "SELECT * FROM tasks WHERE id=?",
        (id,)
    )

    task = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_task.html",
        task=task
    )

@app.route("/delete/<int:id>")
def delete_task(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/stats")
def stats():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=?",
        (session["user_id"],)
    )
    total_tasks = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=? AND status=1",
        (session["user_id"],)
    )
    completed_tasks = cursor.fetchone()[0]

    pending_tasks = total_tasks - completed_tasks

    if total_tasks > 0:
        progress = int((completed_tasks / total_tasks) * 100)
    else:
        progress = 0

    conn.close()

    return render_template(
        "stats.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        progress=progress
    )

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, email FROM users WHERE id=?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        name=user[0],
        email=user[1]
    )

@app.route("/export_csv")
def export_csv():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tasks, created_at, priority, due_date, status FROM tasks WHERE user_id=?",
        (session["user_id"],)
    )

    tasks = cursor.fetchall()
    conn.close()

    def generate():
        yield "Task,Created At,Priority,Due Date,Status\n"

        for task in tasks:
            status = "Completed" if task[4] == 1 else "Pending"

            yield f"{task[0]},{task[1]},{task[2]},{task[3]},{status}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=tasks.csv"
        }
    )

@app.route("/export_pdf")
def export_pdf():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT tasks, created_at, priority, due_date, status
        FROM tasks
        WHERE user_id=?
        """,
        (session["user_id"],)
    )

    tasks = cursor.fetchall()
    conn.close()

    pdf_file = "tasks.pdf"

    p = canvas.Canvas(pdf_file)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, "Smart Task Manager")

    y = 760

    for task in tasks:

        status = "Completed" if task[4] == 1 else "Pending"

        line = (
            f"Task: {task[0]} | "
            f"Priority: {task[2]} | "
            f"Status: {status}"
        )

        p.setFont("Helvetica", 10)
        p.drawString(50, y, line)

        y -= 20

        if y < 50:
            p.showPage()
            y = 800

    p.save()

    return send_file(
        pdf_file,
        as_attachment=True
    )

@app.route("/logout")
def logout():

    session.pop("username", None)
    session.pop("user_id" , None)

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)