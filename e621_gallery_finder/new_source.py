import base64
import dataclasses
import datetime
from typing import Optional, List, Dict


def clean_direct_link(direct_link: Optional[str]) -> Optional[str]:
    if direct_link is None:
        return None
    direct_link = replace_prefix(direct_link, "http://", "https://")
    direct_link = replace_prefix(direct_link, "https://d.facdn.net/", "https://d.furaffinity.net/")
    direct_link = replace_prefix(direct_link, "https://d2.facdn.net/", "https://d.furaffinity.net/")
    return direct_link


def post_to_url(site_id: str, post_id: str, username: Optional[str] = None) -> str:
    return {
        "e621": f"https://e621.net/posts/{post_id}/",
        "fa": f"https://www.furaffinity.net/view/{post_id}/",
        "twitter": f"https://twitter.com/{username or 'user'}/status/{post_id}"
    }[site_id]


def replace_prefix(source: str, old_prefix: str, new_prefix: str) -> str:
    if source.startswith(old_prefix):
        return new_prefix + source[len(old_prefix):]
    return source


@dataclasses.dataclass
class NewSource:
    submission_link: str
    direct_link: Optional[str]

    def source_links(self) -> List[str]:
        new_sources = [self.submission_link]
        if self.direct_link is not None:
            new_sources.append(self.direct_link)
        return new_sources

    @classmethod
    def from_snapshot(cls, snapshot: Dict, suspected_username: Optional[str] = None) -> "NewSource":
        submission_url = post_to_url(snapshot['website_id'], snapshot['site_submission_id'], suspected_username)
        direct_link = clean_direct_link(snapshot["submission_data"]["files"][0]["file_url"])
        return cls(submission_url, direct_link)


@dataclasses.dataclass
class PostStatusEntry:
    post_id: str
    skip_date: Optional[datetime.datetime]
    last_checked: datetime.datetime

    @property
    def post_link(self) -> str:
        return f"https://e621.net/posts/{self.post_id}"


@dataclasses.dataclass
class NewSourceEntry(NewSource):
    source_id: int
    checked: bool
    approved: Optional[bool]

    @property
    def skip_date_format(self) -> str:
        if self.skip_date is None:
            return "None"
        return self.skip_date.isoformat()
    
    @property
    def direct_link_fallback(self) -> Optional[str]:
        if self.direct_link is None:
            return None
        fallback_url = "https://hotlink.spangle.org.uk/img/" + base64.b64encode(self.direct_link.encode()).decode()
