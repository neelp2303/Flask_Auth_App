from flask import Flask, request, render_template, redirect, session, g
import sqlite3
import bcrypt  # type: ignore

app = Flask(__name__)
app.secret_key = "secret_key"

DATABASE = "database.db"


# Function to get database connection
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Return results as dictionaries
    return g.db


# Initialize Database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """
        )
        cursor.execute('''CREATE TABLE IF NOT EXISTS blogs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        author TEXT NOT NULL)''')
        conn.commit()
        # conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password),
            )
            db.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email already exists!")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and bcrypt.checkpw(
            password.encode("utf-8"), user["password"].encode("utf-8")
        ):
            session["email"] = user["email"]
            return redirect("/homepage")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "email" in session:
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (session["email"],)
        ).fetchone()
        return render_template("dashboard.html", user=user)

    return redirect("/login")


@app.route("/create_blog", methods=["GET", "POST"])
def create_blog():
    if "email" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        author = session["email"]

        db = get_db()
        db.execute(
            "INSERT INTO blogs (title, content, author) VALUES (?, ?, ?)",
            (title, content, author),
        )
        db.commit()

        return redirect("/homepage")

    return render_template("create_blog.html")


@app.route("/homepage")
def homepage():
    if 'email' in session:
        db = get_db()
        blogs = db.execute("SELECT * FROM blogs ORDER BY id DESC").fetchall()
    return render_template("homepage.html", blogs=blogs)

        

@app.route("/logout")
def logout():
    session.pop("email", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
