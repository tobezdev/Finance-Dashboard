from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import smtplib
import random
import string
import json
import uuid
import yaml
import os


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = str(uuid.uuid4())
db = SQLAlchemy(app)
login_mgr = LoginManager()
login_mgr.init_app(app)
login_mgr.login_view = "login"  #pyright:ignore[reportAttributeAccessIssue]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    password = db.Column(db.String(150), nullable=False)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    user = db.relationship("User", backref=db.backref("transactions", lazy=True))


with app.app_context():
    db.create_all()


@login_mgr.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            print(f"New successful login to account '{user.username}' from IP: '{request.remote_addr}' .")
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)   #pyright:ignore[reportCallIssue]
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        except IntegrityError:
            db.session.rollback()
            return render_template(
                "register.html",
                error="Username already exists. Please choose a different one.",
            )
    return render_template("register.html")


@app.route('/reset-password', methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]
        user = User.query.filter_by(username=username).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return redirect(url_for("login"))
        else:
            return render_template("reset_password.html", error="User not found")
    return render_template("reset_password.html")


@app.route('/send-otp', methods=["POST"])
def send_otp():
    data = request.get_json()
    if not data:
        return json.dumps({"success": False, "message": "Invalid request data"})
    username_email = data.get("username_email")
    user = User.query.filter((User.username == username_email) | (User.email == username_email)).first()
    if user:
        otp = ''.join(random.choices(string.ascii_letters, k=8))

        try:
            smtp_client = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_client.starttls()
            smtp_client.login('your_email@gmail.com', 'your_email_password')
            smtp_client.sendmail(
                from_addr='your_email@gmail.com', 
                to_addrs=user.email, 
                msg=f"Subject: Your OTP\n\nYour OTP is: {otp}"
            )
            smtp_client.quit()
        except Exception as e:
            return json.dumps({"success": False, "message": str(e)})

        return json.dumps({"success": True})
    return json.dumps({"success": False, "message": "User not found"})


@app.route('/guide', methods=["GET"])
def guide():
    return render_template('guide.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    total_profit_loss = sum(
        transaction.amount if transaction.type == "income" else -transaction.amount
        for transaction in transactions
    ).__round__(2)

    return render_template("index.html", transactions=transactions, total_profit_loss=total_profit_loss)


@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    description = request.form["description"]
    amount = float(request.form["amount"])
    type = request.form["type"]
    date_str = request.form.get("date")
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M") if date_str else None
    new_transaction = Transaction(
        user_id=current_user.id,        #pyright:ignore[reportCallIssue]
        description=description,        #pyright:ignore[reportCallIssue]
        amount=amount,                  #pyright:ignore[reportCallIssue]
        type=type.capitalize(),         #pyright:ignore[reportCallIssue]
        date=date or datetime.now(),    #pyright:ignore[reportCallIssue]
    )
    db.session.add(new_transaction)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/remove/<int:transaction_id>", methods=["POST"])
@login_required
def remove_transaction(transaction_id):
    transaction_to_delete = Transaction.query.get_or_404(transaction_id)
    if transaction_to_delete.user_id != current_user.id:
        return redirect(url_for("index"))
    db.session.delete(transaction_to_delete)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    dir = os.path.dirname(os.path.realpath(__file__))
    file = os.path.join(dir, "config.yml")
    with open(file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        host = config['server_host']
        port = config['server_port']
        debug = config['debug_mode']
        f.close()
    app.run(host=host, port=port, debug=debug)