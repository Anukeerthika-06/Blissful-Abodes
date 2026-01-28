from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# 🔥 ALL 9 ROOMS
ROOMS = [
    {"id": 1, "name": "Deluxe Room", "price": 2500, "capacity": 2, "image": "images/deluxe.jpg"},
    {"id": 2, "name": "Family Suite", "price": 4200, "capacity": 4, "image": "images/family_suite.jpg"},
    {"id": 3, "name": "Single Room", "price": 1500, "capacity": 1, "image": "images/single.png"},
    {"id": 4, "name": "Executive Suite", "price": 3500, "capacity": 2, "image": "images/executive_suite.jpg"},
    {"id": 5, "name": "Premium Villa", "price": 12000, "capacity": 6, "image": "images/premium_villa.avif"},
    {"id": 6, "name": "Superior Double", "price": 2200, "capacity": 2, "image": "images/superior_double.jpg"},
    {"id": 7, "name": "Penthouse Suite", "price": 8500, "capacity": 4, "image": "images/penthouse.jpg"},
    {"id": 8, "name": "Economy Twin", "price": 1800, "capacity": 2, "image": "images/economy_twin.jpg"},
    {"id": 9, "name": "Junior Suite", "price": 3200, "capacity": 3, "image": "images/junior_suite.jpeg"}
]

# 🔐 USERS STORED AS: username -> password, role
USERS = {}

def init_admin():
    # Default admin account
    USERS['admin'] = {'password': 'admin123', 'role': 'admin'}

# ---------------- HOME ----------------
@app.route('/')
@app.route('/home')
@app.route('/index')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ---------------- USER LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # match your login HTML
        password = request.form.get('password')

        if username in USERS and USERS[username]['password'] == password:
            session['user'] = username
            session['role'] = USERS[username]['role']

            if USERS[username]['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))

        flash('Invalid username or password')

    return render_template('login.html')

# ---------------- USER SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password or not confirm_password:
            return render_template('signup.html', error='All fields are required')

        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')

        if username in USERS:
            return render_template('signup.html', error='Username already exists')

        USERS[username] = {'password': password, 'role': 'user'}
        flash('Signup successful! Please login.')
        return redirect(url_for('login'))

    return render_template('signup.html')

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')  # HTML input name="username"
        password = request.form.get('password')

        if username in USERS and USERS[username]['password'] == password and USERS[username]['role'] == 'admin':
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        flash('Admin credentials invalid')

    return render_template('admin_login.html')

# ---------------- ADMIN SIGNUP ----------------
@app.route('/admin-signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('admin_signup.html', error='All fields are required')

        USERS[username] = {'password': password, 'role': 'admin'}
        flash('Admin account created successfully!')
        return redirect(url_for('admin_login'))

    return render_template('admin_signup.html')

# ---------------- SEARCH ----------------
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests')

        available_rooms = [r for r in ROOMS if r['capacity'] >= int(guests or 1)]

        return render_template(
            'search.html',
            rooms=available_rooms,
            check_in=check_in,
            check_out=check_out,
            guests=guests
        )

    return redirect(url_for('index'))

# ---------------- BOOKING ----------------
@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    room = next((r for r in ROOMS if r['id'] == room_id), None)
    if not room:
        flash('Room not found!')
        return redirect(url_for('index'))

    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    guests = request.args.get('guests')

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        check_in = request.form.get('check_in') or check_in
        check_out = request.form.get('check_out') or check_out
        guests = request.form.get('guests') or guests

        checkin_date = datetime.strptime(check_in, '%Y-%m-%d')
        checkout_date = datetime.strptime(check_out, '%Y-%m-%d')
        nights = (checkout_date - checkin_date).days
        total_price = room['price'] * nights

        flash(
            f'✅ Booking confirmed! {name} - {room["name"]} ({nights} nights, ₹{total_price})',
            'success'
        )
        return redirect(url_for('index'))

    return render_template(
        'booking.html',
        room=room,
        check_in=check_in,
        check_out=check_out,
        guests=guests
    )

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('user'))

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin-dashboard')
def admin_dashboard():
    # Allow only admin users
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    # Dashboard statistics
    stats = {
        'users': len(USERS),      # total registered users
        'rooms': len(ROOMS),      # total rooms (9)
        'bookings': 0             # static (no booking storage yet)
    }

    return render_template(
        'admin_dashboard.html',
        user=session.get('user'),
        stats=stats
    )


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    init_admin()  # create default admin account
    app.run(debug=True, host='0.0.0.0', port=5000)
