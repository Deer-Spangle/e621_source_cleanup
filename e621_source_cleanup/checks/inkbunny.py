from typing import Optional

from e621_source_cleanup.checks.base import URLCheck, SourceURL, SourceMatch


class AnchorTag(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain_clean != "inkbunny.net":
            return None
        if "#" in source_url.path:
            path, _ = source_url.path.split("#", 1)
            fix_url = f"https://{source_url.domain}/{path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Inkbunny links with unnecessary anchors"
            )
        return None

