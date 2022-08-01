from typing import Optional

from e621_source_cleanup.checks.base import SourceURL, SourceMatch, URLCheck


class TwitFixCheck(URLCheck):
    def __init__(self):
        self.twitfix_domains = [
            "vxtwitter.com",
            "ayytwitter.com",
            "fxtwitter.com",
            "pxtwitter.com",
            "twitter64.com",
            "twittpr.com",
        ]

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        source_domain = source_url.domain_clean
        if source_domain is None:
            return None
        if source_domain in self.twitfix_domains:
            return SourceMatch(
                post_id,
                source_url.raw,
                f"https://twitter.com/{source_url.path}",
                self,
                f"TwitFix domain {source_domain} changed to direct twitter link"
            )


class TwitterTracking(TwitFixCheck):

    def __init__(self):
        super().__init__()
        self.twitter_urls = self.twitfix_domains + ["twitter.com"]

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.path:
            return None
        if source_url.domain_clean not in self.twitter_urls:
            return None
        if "?" not in source_url.path:
            return None
        cleaned_path, _ = source_url.path.split("?", 1)
        return SourceMatch(
            post_id,
            source_url.raw,
            f"https://twitter.com/{cleaned_path}",
            self,
            "Twitter link had tracking info attached"
        )
