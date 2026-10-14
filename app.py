from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

inventory = [
    {"id": 1, "item": "Laptop", "quantity": 10},
    {"id": 2, "item": "Mouse", "quantity": 25}
]

@app.route("/")
def index():
    return render_template("index.html", inventory=inventory)

@app.route("/add", methods=["POST"])
def add_item():
    item_name = request.form.get("item")
    qty = request.form.get("quantity")
    if item_name and qty:
        inventory.append({"id": len(inventory) + 1, "item": item_name, "quantity": int(qty)})
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
