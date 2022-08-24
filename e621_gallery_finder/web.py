import base64
import dataclasses
import datetime
import json
from pathlib import Path
from typing import Tuple, List, Optional

import flask

from e621_gallery_finder.database import Database
from e621_gallery_finder.e621_api import E621API
from e621_gallery_finder.new_source import NewSource, NewSourceEntry, PostStatusEntry


templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
app = flask.Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
db = Database()
config_path = "./config.json"
with open(config_path, "r") as conf_file:
    config = json.load(conf_file)
api = E621API(
    "e621_gallery_finder/1.0.0 (by dr-spangle on e621)",
    "dr-spangle",
    config["e621_api_key"]
)

AUTH_KEY = config["web_auth_key"]


@app.route('/')
def hello():
    return flask.render_template(
        "home.html",
        unchecked_sources=db.count_unchecked_sources(),
        total_sources=db.count_total_sources(),
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
    new_data = db.get_next_unchecked_sources()
    if not new_data:
        return None
    post_status, new_sources = next_data[0]
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
        return flask.render_template(
            "check_post.html",
            message="Post skipped.",
            post_id=post_id,
        )
    if action == "no_match":
        for source_id in source_ids:
            db.update_source_approved(source_id, False)
        return flask.render_template(
            "check_post.html",
            message="Marked sources as no match.",
            post_id=post_id,
        )
    if action == "match_all":
        sources = []
        for source_id in source_ids:
            sources.append(db.get_source(source_id))
        source_links = sum([source.source_links() for source in sources], start=[])
        api.add_new_sources(post_id, source_links)
        for source_id in source_ids:
            db.update_source_approved(source_id, True)
        return flask.render_template(
            "check_post.html",
            message="Added source links for e621 post.",
            post_id=post_id,
        )


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


@app.route("/list_next.json")
def list_next():
    if flask.request.cookies["auth_key"] != AUTH_KEY:
        return {
            "error": {
                "code": 403,
                "message": "Not logged in"
            }
        }, 403
    results = []
    new_data = db.get_next_unchecked_sources(count=20)
    for post_status, new_sources in new_data:
        resp = api.get_post(post_status.post_id)
        post_status_json = post_status.to_json()
        post_status_json["direct_link"] = resp["post"]["file"]["url"]
        results.append(
            {
                "post_status": post_status_json,
                "new_sources": [
                    new_source.to_json() for new_source in new_sources
                ]
            }
        )
    return {
        "data": {
            "results": results
        }
    }
