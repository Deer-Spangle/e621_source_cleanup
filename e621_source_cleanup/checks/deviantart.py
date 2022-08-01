from typing import Optional

from e621_source_cleanup.checks.base import URLCheck, SourceURL, SourceMatch


class OldFormatUserPage(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.domain.endswith("deviantart.com"):
            return None
        if source_url.domain_clean.endswith(".deviantart.com"):
            username, _ = source_url.domain.split(".", 1)
            fix_url = f"https://deviantart.com/{username}/{source_url.path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Source uses the old deviantart subdomain URL format"
            )
        return None
