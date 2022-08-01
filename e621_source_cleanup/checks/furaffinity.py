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
                self.__class__,
                "FA link was to a specific comment"
            )
