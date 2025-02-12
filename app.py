import io
from flask import Flask, request, render_template, redirect, send_file, session, g
import sqlite3
import bcrypt  # type: ignore
from flask_ngrok import run_with_ngrok

app = Flask(__name__)
app.secret_key = "secret_key"
# run_with_ngrok(app)
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
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS blogs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        author TEXT NOT NULL,
                        email TEXT NOT NULL,
                        image BLOB
                        )"""
        )
        conn.commit()
        # conn.close()


init_db()


@app.route("/get_image/<int:blog_id>")
def get_image(blog_id):
    db = get_db()
    blog = db.execute("SELECT image FROM blogs WHERE id = ?", (blog_id,)).fetchone()

    if blog and blog["image"]:
        return send_file(
            io.BytesIO(blog["image"]), mimetype="image/jpeg", as_attachment=False
        )

    return "No Image", 404


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
            session["name"] = user["name"]
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
        author = session["name"]
        email = session["email"]

        # Handle image upload
        image_data = None
        if "image" in request.files:
            image = request.files["image"]
            if image and image.filename != "":
                image_data = image.read()  # Read image as binary data

        # Insert blog into database with image
        db = get_db()
        db.execute(
            "INSERT INTO blogs (title, content, author, email, image) VALUES (?, ?, ?, ?, ?)",
            (title, content, author, email, image_data),
        )
        db.commit()

        return redirect("/homepage")

    return render_template("create_blog.html")


@app.route("/homepage")
def homepage():
    if "email" in session:
        db = get_db()
        blogs = db.execute("SELECT * FROM blogs ORDER BY id DESC").fetchall()
    return render_template("homepage.html", blogs=blogs)


@app.route("/delete_blog/<int:blog_id>", methods=["POST"])
def delete_blog(blog_id):
    if "email" not in session:
        return redirect("/login")

    db = get_db()
    blog = db.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,)).fetchone()

    # Ensure the logged-in user is the author
    if blog and blog["email"] == session["email"]:
        db.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
        db.commit()

    return redirect("/homepage")


@app.route("/my_blogs")
def my_blogs():
    if "email" not in session:
        return redirect("/login")

    db = get_db()
    user_blogs = db.execute(
        "SELECT * FROM blogs WHERE author = ?", (session["name"],)
    ).fetchall()

    return render_template("user_blog.html", blogs=user_blogs)


@app.route("/logout")
def logout():
    session.pop("email", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
