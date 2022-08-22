import datetime
import time
from typing import List, Dict

import requests
import requests.auth


class E621API:
    def __init__(self, user_agent: str, username: str, api_key: str):
        self.user_agent = user_agent
        self.username = username
        self.api_key = api_key
        self.last_call = None

    def wait_before_call(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.last_call is None:
            self.last_call = now
            return
        while (now - self.last_call).total_seconds() < 1:
            time.sleep(0.1)
            now = datetime.datetime.now(datetime.timezone.utc)
        self.last_call = now
        return

    def _get(self, url: str) -> Dict:
        self.wait_before_call()
        return requests.get(
            url,
            headers={
                "User-Agent": self.user_agent
            }
        ).json()

    def _patch(self, url: str, json_data: Dict) -> Dict:
        self.wait_before_call()
        return requests.patch(
            url,
            headers={
                "User-Agent": self.user_agent
            },
            data=json_data,
            auth=requests.auth.HTTPBasicAuth(self.username, self.api_key)
        ).json()

    def add_new_sources(self, post_id: str, new_source_links: List[str]) -> None:
        current_post = self._get(f"https://e621.net/posts/{post_id}.json")
        current_sources = current_post["post"]["sources"]
        add_sources = set(new_source_links) - set(current_sources)
        if not add_sources:
            print(f"No need to add sources for post {post_id}")
            return
        source_diff = "\n".join(f"{source_link}" for source_link in add_sources)
        resp = self._patch(
            f"https://e621.net/posts/{post_id}.json",
            {
                "post[source_diff]": source_diff,
                "post[edit_reason]": "Adding additional source links (e621_gallery_finder script)"
            }
        )
        print(resp)
