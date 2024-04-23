from flask import Flask, render_template, request

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    message = request.form["message"]
    return message

@app.route("/submit/<username>", methods=["POST"])
def submit_username(username):
    username = request.form["username"]
    return username

if __name__ == "__main__":
    app.run(debug=True)
