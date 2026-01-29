from flask import Flask, render_template, request, redirect, url_for, session
import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = "hotel_secret_key"

# ---------------- AWS CONFIG ----------------
REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:539247489202:aws_bliss_ai"

# EXISTING TABLES (DO NOT CHANGE NAMES)
users_table = dynamodb.Table("users_table")
admins_table = dynamodb.Table("admins_table")
rooms_table = dynamodb.Table("rooms_table")
bookings_table = dynamodb.Table("bookings_table")

# ---------------- SNS FUNCTION ----------------
def send_notification(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print("SNS Error:", e)

# ---------------- BASIC ROUTES ----------------
@app.route("/")
def index():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- USER AUTH ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = users_table.get_item(Key={"email": email})
        if "Item" in response:
            return "User already exists"

        users_table.put_item(Item={
            "email": email,
            "password": password
        })

        send_notification("New User Signup", f"{email} registered")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = users_table.get_item(Key={"email": email})

        if "Item" in response and response["Item"]["password"] == password:
            session.clear()
            session["user"] = email
            session["role"] = "user"
            send_notification("User Login", f"{email} logged in")
            return redirect(url_for("dashboard"))

        return "Invalid username or password"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    email = session["user"]

    response = bookings_table.query(
        KeyConditionExpression=Key("user_email").eq(email)
    )

    bookings = response.get("Items", [])
    return render_template("dashboard.html", bookings=bookings)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------- SEARCH & BOOKING ----------------
@app.route("/search")
def search():
    rooms = rooms_table.scan().get("Items", [])
    return render_template("search.html", rooms=rooms)


@app.route("/book/<room_id>", methods=["GET", "POST"])
def book(room_id):
    if "user" not in session:
        return redirect(url_for("login"))

    room = rooms_table.get_item(Key={"room_id": room_id}).get("Item")

    if not room:
        return "Room not found"

    if request.method == "POST":
        booking_id = str(uuid.uuid4())

        bookings_table.put_item(Item={
            "user_email": session["user"],
            "booking_id": booking_id,
            "room_name": room["name"],
            "check_in": request.form["check_in"],
            "check_out": request.form["check_out"],
            "guests": request.form["guests"],
            "date": datetime.now().strftime("%Y-%m-%d")
        })

        send_notification(
            "Room Booked",
            f"{session['user']} booked {room['name']}"
        )

        return render_template("success.html", room=room)

    return render_template("booking.html", room=room)

# ---------------- ADMIN AUTH ----------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        response = admins_table.get_item(Key={"username": username})

        if "Item" in response and response["Item"]["password"] == password:
            session.clear()
            session["admin"] = username
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))

        return "Invalid Admin Login"

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    users = users_table.scan().get("Items", [])
    rooms = rooms_table.scan().get("Items", [])
    bookings = bookings_table.scan().get("Items", [])

    stats = {
        "total_users": len(users),
        "total_rooms": len(rooms),
        "total_bookings": len(bookings),
        "today_bookings": len([
            b for b in bookings
            if b.get("date") == datetime.now().strftime("%Y-%m-%d")
        ])
    }

    return render_template(
        "admin_dashboard.html",
        admin=session.get("admin"),
        users=users,
        rooms=rooms,
        bookings=bookings,
        stats=stats
    )


@app.route("/admin/add-room", methods=["GET", "POST"])
def add_room():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        room_id = str(uuid.uuid4())

        rooms_table.put_item(Item={
            "room_id": room_id,
            "name": request.form["name"],
            "price": request.form["price"],
            "capacity": request.form["capacity"]
        })

        send_notification("New Room Added", request.form["name"])
        return redirect(url_for("admin_dashboard"))

    return render_template("add_room.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
