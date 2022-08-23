import base64
import dataclasses
import datetime
from typing import Tuple, List, Optional

import flask

from e621_gallery_finder.database import Database
from e621_gallery_finder.e621_api import E621API
from e621_gallery_finder.new_source import NewSource, NewSourceEntry, PostStatusEntry


templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
app = flask.Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
db = Database()
api = E621API(
    "e621_gallery_finder/1.0.0 (by dr-spangle on e621)",
    "dr-spangle",
    ""
)

AUTH_KEY = ""


@app.route('/')
def hello():
    return flask.render_template(
        "home.html",
        unchecked_sources = db.count_unchecked_sources(),
        total_sources = db.count_total_sources(),
    )


@app.route("/login")
def login_form():
    return flask.render_template(
        "login.html"
    )


@app.route("/login", methods=["POST"])
def login_post():
    auth_key = flask.request.form["auth_key"]
    if auth_key != AUTH_KEY:
        return "Invalid auth token"
    resp = flask.make_response("Logged in")
    resp.set_cookie("auth_key", auth_key, max_age=86400*100)
    return resp


def get_next_post() -> Optional[Tuple[PostStatusEntry, List[NewSourceEntry]]]:
    next_data = db.get_next_unchecked_source()
    if next_data is None:
        return None
    post_data, sources_data = next_data
    post_status = PostStatusEntry(post_data[0], post_data[1], post_data[2])
    new_sources = []
    for source_data in sources_data:
        new_sources.append(NewSourceEntry(source_data[1], source_data[2], source_data[0], source_data[3], source_data[4]))
    return post_status, new_sources


@app.route("/check", methods=["POST"])
def record_match():
    if flask.request.cookies["auth_key"] != AUTH_KEY:
        return "Not logged in."
    post_id = flask.request.form["post_id"]
    source_ids = [int(x) for x in flask.request.form["source_ids"].split(",")]
    action = flask.request.form["action"]
    if action == "skip":
        db.update_post_skip(post_id, datetime.datetime.now(datetime.timezone.utc))
        return "Post skipped. <a href=\"/check\">Click here for another</a>"
    if action == "no_match":
        for source_id in source_ids:
            db.update_source_approved(source_id, False)
        return "Marked sources as no match. <a href=\"/check\">Click here for another</a>"
    if action == "match_all":
        sources = []
        for source_id in source_ids:
            sid, post_id, submission_link, direct_link, checked, approved = db.get_source(source_id)
            sources.append(NewSourceEntry(submission_link, direct_link, sid, checked, approved))
        source_links = sum([source.source_links() for source in sources], start=[])
        api.add_new_sources(post_id, source_links)
        for source_id in source_ids:
            db.update_source_approved(source_id, True)
        return f"Added sources for <a href=\"https://e621.net/posts/{post_id}\">e621 post</a>. <a href=\"/check\">Click here for another</a>"


@app.route("/check")
def check_match():
    if flask.request.cookies["auth_key"] != AUTH_KEY:
        return "Not logged in."
    next_data = get_next_post()
    if next_data is None:
        return "No more matches to check!"
    post_status, new_sources = next_data
    post_resp = api.get_post(post_status.post_id)
    post_direct_url = post_resp["post"]["file"]["url"]
    return flask.render_template(
        "check.html",
        post_status=post_status,
        new_sources=new_sources,
        post_direct_url=post_direct_url,
    )
