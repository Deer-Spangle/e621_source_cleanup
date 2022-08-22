import flask

from e621_gallery_finder.database import Database

app = flask.Flask(__name__)
db = Database()


@app.route('/')
def hello():
    return f"""
<html>
<body>
Welcome to the e621 source adding UI This should present you with 2 or 3 images, 
and you confirm whether they match. Easy!<br/>
There are: {db.count_unchecked_sources()} unchecked sources.
"""


@app.route("/login")
def login_form():
    return """
<html>
<body>
<form action="/login" method="post">
Password: <input type="password" name="auth_key" /><br />
<input type="submit" />
</form>
</body>
</html>
"""


@app.route("/login", methods=["POST"])
def login_post():
    auth_key = flask.request.form["auth_key"]
    resp = flask.make_response("Logged in")
    resp.set_cookie("auth_key", auth_key, max_age=86400*100)
    return resp
