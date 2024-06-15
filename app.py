from flask import Flask, render_template, request, redirect, url_for, session
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
import yaml

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
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


@login_manager.user_loader
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
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="sha256")
        new_user = User(username=username, password=hashed_password)
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

    return render_template(
        "index.html", transactions=transactions, total_profit_loss=total_profit_loss
    )


@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    description = request.form["description"]
    amount = float(request.form["amount"])
    type = request.form["type"]
    date_str = request.form.get("date")
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M") if date_str else None
    new_transaction = Transaction(
        user_id=current_user.id,
        description=description,
        amount=amount,
        type=type,
        date=date or datetime.now(),
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
    with open('config.yml', 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        host = config['server_host']
        port = config['server_port']
        debug = config['debug_mode']
        f.close()
    app.run(host=host, port=port, debug=debug)