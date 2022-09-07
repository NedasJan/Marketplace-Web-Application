import os
import sqlite3
import bcrypt
import uuid

from flask import Flask, redirect, render_template, request, session
from flask_session import Session

from tools import *


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure folder where images will be stored
app.config["UPLOAD_FOLDER"] = "static/images/"

# Connect to the database
connection = sqlite3.connect("market.db", check_same_thread=False)
database = connection.cursor()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Show listings"""

    # Get listings from the database
    database.execute(
        "SELECT id, image_name, title, price FROM listings ORDER BY date DESC")
    listings = database.fetchall()

    return render_template("index.html", heading="Listings", listings=listings)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure first name was submitted
        if not request.form.get("first_name"):
            return render_template("register.html", error_message="Must provide your first name!")

        # Ensure first name was submitted
        if not request.form.get("last_name"):
            return render_template("register.html", error_message="Must provide your last name!")

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("register.html", error_message="Must provide a username!")

        # Ensure the username is not already used
        database.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?", (request.form.get("username"),))
        if database.fetchone()[0] != 0:
            return render_template("register.html", error_message="Username already exists!")

        # Ensure the email address was submitted
        if not request.form.get("email_address"):
            return render_template("register.html", error_message="Must provide your first name!")

        # Ensure the email address contains '@'
        if "@" not in request.form.get("email_address"):
            return render_template("register.html", error_message="Invalid email address!")

        # Ensure the email is not already used
        database.execute("SELECT COUNT(*) FROM users WHERE email_address = ?",
                         (request.form.get("email_address"),))
        if database.fetchone()[0] != 0:
            return render_template("register.html", error_message="Email address is already in use!")

        # Ensure password was submitted
        if not request.form.get("password"):
            return render_template("register.html", error_message="Must provide a password!")

        # Ensure password confirmation was submitted
        if not request.form.get("password"):
            return render_template("register.html", error_message="Must provide a password confirmation!")

        # Ensure password and password confirmation are matching
        if request.form.get("password") != request.form.get("password_confirmation"):
            return render_template("register.html", error_message="Passwords don't match!")

        # Generate a random salt for the hash function
        password_salt = bcrypt.gensalt()

        # Encrypt the password
        password_hash = bcrypt.hashpw(request.form.get(
            "password").encode("utf-8"), password_salt)

        # Insert data of a new user into a database
        database.execute("INSERT INTO users (first_name, last_name, username, email_address, password_hash) VALUES(?, ?, ?, ?, ?)", (request.form.get(
            "first_name"), request.form.get("last_name"), request.form.get("username"), request.form.get("email_address"), password_hash))
        connection.commit()

        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username or email address was submitted
        if not request.form.get("identification"):
            return render_template("login.html", error_message="Must provide a username or email address!")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error_message="Must provide a password!")

        # Query database for email address or username
        if "@" in request.form.get("identification"):
            database.execute("SELECT * FROM users WHERE email_address = ?",
                             (request.form.get("identification"),))

        else:
            database.execute("SELECT * FROM users WHERE username = ?",
                             (request.form.get("identification"),))

        user = database.fetchone()

        # Ensure username exists
        if user == None:
            return render_template("login.html", error_message="Username doesn't exist!")

        # Ensure password is correct
        if not bcrypt.checkpw(request.form.get("password").encode("utf-8"), user[5]):
            return render_template("login.html", error_message="Invalid password!")

        # Remember which user has logged in
        session["user_id"] = user[0]
        session["username"] = user[3]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Clear user's session
    session.clear()

    return redirect("/")


@app.route("/used")
def used():
    """Show used listings"""

    # Select listings which have "condition" value equal to "used"
    database.execute(
        "SELECT id, image_name, title, price FROM listings WHERE condition = 'used' ORDER BY date DESC")
    listings = database.fetchall()

    return render_template("index.html", heading="Used items", listings=listings)


@app.route("/new")
def new():
    """Show new listings"""

    # Select listings which have "condition" value equal to "new"
    database.execute(
        "SELECT id, image_name, title, price FROM listings WHERE condition = 'new' ORDER BY date DESC")
    listings = database.fetchall()

    return render_template("index.html", heading="New items", listings=listings)


@app.route("/list", methods=["GET", "POST"])
@login_required
def list():
    """List an item"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure title was submitted
        if not request.form.get("title"):
            return render_template("list.html", error_message="Title cannot be empty!")

        # Ensure description was submitted
        if not request.form.get("description"):
            return render_template("list.html", error_message="Description cannot be empty!")

        # Ensure city was submitted
        if not request.form.get("city"):
            return render_template("list.html", error_message="City condition cannot be empty!")

        # Ensure condition was submitted
        if not request.form.get("condition"):
            return render_template("list.html", error_message="Item condition cannot be empty!")

        # Ensure condition is valid
        if request.form.get("condition").lower() != "new" and request.form.get("condition").lower() != "used":
            return render_template("list.html", error_message="Invalid item condition!")

        # Ensure price is was submitted
        if not request.form.get("price"):
            return render_template("list.html", error_message="Price cannot be empty!")

        price = request.form.get("price").replace(",", ".")

        # Ensure price is valid
        if not isfloat(price):
            return render_template("list.html", error_message="Invalid price!")

        # Ensure the image was submitted
        if not request.files["image"]:
            return render_template("list.html", error_message="Image must be submitted!")

        # Ensure the image exists
        image = request.files['image']
        if not image:
            return render_template("list.html", error_message="Invalid image!")

        # Ensure the image has a name
        if image.filename == "":
            return render_template("list.html", error_message="Invalid image name!")

        # Ensure the image has a valid format
        if not allowed_file(image.filename):
            return render_template("list.html", error_message="Invalid image format!")

        # Hash the filename of an image
        filename = str(uuid.uuid4()) + "." + \
            image_format(ALLOWED_EXTENSIONS, image.filename)

        # Save the image in the file system
        image.save(app.config["UPLOAD_FOLDER"] + filename)

        # Insert the data into a database
        database.execute("INSERT INTO listings (user_id, image_name, title, description, city, condition, price, date) VALUES(?, ?, ?, ?, ?, ?, ?, DATETIME('now'))", (
            session["user_id"], filename, request.form.get("title"), request.form.get("description"), request.form.get("city"), request.form.get("condition").lower(), request.form.get("price")))
        connection.commit()

        return render_template("list.html", heading="Edit a listing", message="Your item was listed successfully!")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("list.html", heading="List an item")


@app.route("/details")
def details():
    """Show listing details"""

    # Select the required information about the listing
    database.execute(
        "Select image_name, title, price, condition, city, description, user_id FROM listings WHERE id = ?", (request.args["id"],))
    listing = database.fetchone()

    # Select the email address of a person, who listed an item
    database.execute(
        "SELECT email_address FROM users WHERE id = ?", (listing[6],))
    email_address = database.fetchone()[0]

    return render_template("details.html", listing=listing, email_address=email_address)


@app.route("/listings", methods=["GET", "POST"])
@login_required
def listings():
    """Show listings that the user owns"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        return render_template("listings.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Get user listings from the database
        database.execute(
            "SELECT title, date, price, id FROM listings WHERE user_id = ? ORDER BY date DESC", (session["user_id"],))
        listings = database.fetchall()

        return render_template("listings.html", listings=listings)


@app.route("/delete", methods=["POST"])
@login_required
def delete():
    """Delete a listing"""

    # Get the image name of a listing from the database
    database.execute("SELECT image_name FROM listings WHERE id = ?",
                     (request.form.get("id"),))
    image_name = database.fetchone()[0]

    # Delete the image
    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

    # Delete the listing information from the database
    database.execute("DELETE FROM listings WHERE id = ?",
                     (request.form.get("id"),))
    connection.commit()

    # Get user listings from the database
    database.execute(
        "SELECT title, date, price, id FROM listings WHERE user_id = ? ORDER BY date DESC", (session["user_id"],))
    listings = database.fetchall()

    return render_template("listings.html", message="Listing successfully deleted!", listings=listings)


@app.route("/settings")
@login_required
def settings():
    """Show settings"""

    return render_template("settings.html")


@app.route("/password", methods=["POST"])
@login_required
def changePassword():
    """Change user password"""

    # Ensure old password was submitted
    if not request.form.get("old_password"):
        return render_template("settings.html", error_message="Must provide old password!")

    # Ensure new password was submitted
    if not request.form.get("password"):
        return render_template("settings.html", error_message="Must provide a new password!")

    # Ensure new password confirmation was submitted
    if not request.form.get("confirmation"):
        return render_template("settings.html", error_message="Must provide password confirmation!")

    # Ensure new password and new password confirmation are equal
    if request.form.get("password") != request.form.get("confirmation"):
        return render_template("settings.html", error_message="Passwords don't match!")

    # Select the old password hash from the database
    database.execute(
        "SELECT password_hash FROM users WHERE id = ?", (session["user_id"],))
    password_hash = database.fetchone()[0]

    # Ensure the old is valid
    if not bcrypt.checkpw(request.form.get("old_password").encode("utf-8"), password_hash):
        return render_template("settings.html", error_message="Invalid password!")

    # Generate a random salt for the hash function
    password_salt = bcrypt.gensalt()

    # Encrypt the password
    password_hash = bcrypt.hashpw(request.form.get(
        "password").encode("utf-8"), password_salt)

    # Update password in the database
    database.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (password_hash, session["user_id"],))
    connection.commit()

    return render_template("settings.html", message="Password sucessfully changed!")


@app.route("/search")
def search():
    """Search for listings"""

    # Ensure the search keyword exists
    if not request.args["keyword"]:
        return redirect("/")

    search_keyword = "%" + request.args.get("keyword") + "%"

    # Select listings which satisfy the search
    database.execute("SELECT id, image_name, title, price FROM listings WHERE title LIKE ? OR description LIKE ? OR condition LIKE ?",
                     (search_keyword, search_keyword, search_keyword,))
    listings = database.fetchall()

    return render_template("search.html", listings=listings, search_keyword=request.args.get("keyword"))
