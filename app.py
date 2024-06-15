from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'expense' or 'income'
    date = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    transactions = Transaction.query.all()

    total_profit_loss: float = sum(
        transaction.amount if transaction.type == "income" else -transaction.amount
        for transaction in transactions
    ).__round__(2)

    return render_template(
        "index.html", transactions=transactions, total_profit_loss=total_profit_loss
    )


@app.route("/add", methods=["POST"])
def add_transaction():
    description = request.form["description"]
    amount = float(request.form["amount"])
    type = request.form["type"]
    new_transaction = Transaction(description=description, amount=amount, type=type)
    db.session.add(new_transaction)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/remove/<int:transaction_id>", methods=["POST"])
def remove_transaction(transaction_id):
    transaction_to_delete = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction_to_delete)
    db.session.commit()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=80)