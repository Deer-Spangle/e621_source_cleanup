from typing import List, Optional

from e621_source_cleanup.checks.base import BaseCheck, SourceURL, SourceMatch


class TwitFixCheck(BaseCheck):
    def __init__(self):
        self.twitfix_domains = [
            "vxtwitter.com",
            "ayytwitter.com",
            "fxtwitter.com",
            "pxtwitter.com",
            "twitter64.com",
            "twittpr.com",
        ]

    def matches(self, source_list: List[str], post_id: str) -> Optional[SourceMatch]:
        for source in source_list:
            source_url = SourceURL.decompose_source(source)
            source_domain = source_url.domain.removeprefix("www.")
            if source_domain in self.twitfix_domains:
                return SourceMatch(
                    post_id,
                    source,
                    f"https://twitter.com/{source_url.path}",
                    self.__class__,
                    f"Twitfix domain {source_domain} changed to direct twitter link"
                )
        return None
