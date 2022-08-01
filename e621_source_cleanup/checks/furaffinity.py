from typing import Optional

from e621_source_cleanup.checks.base import URLCheck, SourceURL, SourceMatch


class CommentsLink(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain_clean == "furaffinity.net" and "#cid" in source_url.path:
            cleaned_path, _ = source_url.path.split("#cid", 1)
            return SourceMatch(
                post_id,
                source_url.raw,
                f"https://furaffinity.net/{cleaned_path}",
                self,
                "FA link was to a specific comment"
            )


class OldCDN(URLCheck):

    def __init__(self) -> None:
        super().__init__()
        self.old_cdn_urls = {
            "d.facdn.net",
            "d2.facdn.net"
        }

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain not in self.old_cdn_urls:
            return None
        return SourceMatch(
            post_id,
            source_url.raw,
            f"https://d.furaffinity.net/{source_url.path}",
            self,
            "FA direct image link using old CDN URL"
        )
