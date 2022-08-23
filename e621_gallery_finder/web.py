import base64
import dataclasses
import datetime
from typing import Tuple, List, Optional

import flask

from e621_gallery_finder.database import Database
from e621_gallery_finder.e621_api import E621API
from e621_gallery_finder.new_source import NewSource

app = flask.Flask(__name__)
db = Database()
api = E621API(
    "e621_gallery_finder/1.0.0 (by dr-spangle on e621)",
    "dr-spangle",
    ""
)

AUTH_KEY = ""


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
    if auth_key != AUTH_KEY:
        return "Invalid auth token"
    resp = flask.make_response("Logged in")
    resp.set_cookie("auth_key", auth_key, max_age=86400*100)
    return resp


@dataclasses.dataclass
class PostStatus:
    post_id: str
    skip_date: Optional[datetime.datetime]
    last_checked: datetime.datetime
    _direct_url: Optional[str] = None

    @property
    def post_link(self) -> str:
        return f"https://e621.net/posts/{self.post_id}"

    def direct_url(self) -> str:
        if self._direct_url:
            return self._direct_url
        resp = api.get_post(self.post_id)
        self._direct_url = resp["post"]["file"]["url"]
        return self._direct_url


@dataclasses.dataclass
class NewSourceEntry(NewSource):
    source_id: int
    checked: bool
    approved: Optional[bool]

    @property
    def submission_link_cell_html(self) -> str:
        if self.submission_link is None:
            return "<td>None</td>"
        return f"<td><a href=\"{self.submission_link}\">Link</a></td>"

    @property
    def direct_link_cell_html(self) -> str:
        if self.direct_link is None:
            return "<td>No direct link</td>"
        fallback_url = "https://hotlink.spangle.org.uk/img/" + base64.b64encode(self.direct_link.encode()).decode()
        return f"<td><img style=\"max-width: 100%\" src=\"{self.direct_link}\" onError=\"this.onError=null;this.src='{fallback_url}'\" />"


def get_next_post() -> Optional[Tuple[PostStatus, List[NewSourceEntry]]]:
    next_data = db.get_next_unchecked_source()
    if next_data is None:
        return None
    post_data, sources_data = next_data
    post_status = PostStatus(post_data[0], post_data[1], post_data[2])
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
    return f"""
<html>
<head>
<style>
table, tr, th, td {{
    border: 1px solid black;
    border-collapse: collapse;
}}
th {{
    background-color: #f7dc6f;
}}
th.calculated {{
    background-color: #5dade2;
}}
</style>
</head>
<body>
Post: <a href="{post_status.post_link}">{post_status.post_id}</a><br />
Last checked: {post_status.last_checked.isoformat()}<br />
Skipped: {"N/A" if post_status.skip_date is None else post_status.skip_date.isoformat()}<br />
<br />
<form action="/check" method="post">
<input type="hidden" name="post_id" value="{post_status.post_id}" />
<input type="hidden" name="source_ids" value="{",".join(str(source.source_id) for source in new_sources)}" />
<input type="submit" name="action" value="match_all" />
<input type="submit" name="action" value="skip" />
<input type="submit" name="action" value="no_match" />
</form>
<table>
<tr>
<td>Original</td>
{"".join("<td>New Source</td>" for _ in new_sources)}
</tr>

<tr>
<td><a href="{post_status.post_link}">Post link</a></td>
{"".join(source.submission_link_cell_html for source in new_sources)}
</tr>

<tr>
<td><img style="max-width: 100%" src="{post_status.direct_url()}" /></td>
{"".join(source.direct_link_cell_html for source in new_sources)}

</table>

</body>
</html>
"""
