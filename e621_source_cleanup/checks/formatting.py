from typing import Optional

from e621_source_cleanup.checks.base import SourceMatch, SourceURL, URLCheck


class SpacesInURL(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if " " not in source_url.path:
            return None
        if "." not in source_url.domain:
            return None
        path = source_url.path
        if "?" in source_url.path:
            path, data = source_url.path.split("?", 1)
            cleaned_path = path.replace(" ", "%20") + "?" + path.replace(" ", "+")
        else:
            cleaned_path = path.replace(" ", "%20")
        return SourceMatch(
            post_id,
            source_url.raw,
            f"{source_url.protocol}://{source_url.domain}/{cleaned_path}",
            self,
            "URL has improperly encoded spaces in it"
        )


class TitlecaseDomain(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain in [source_url.domain.title(), source_url.domain.capitalize()]:
            fix_url = f"{source_url.protocol}://{source_url.domain.lower()}/{source_url.path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "The first letter of the source URL is capitalised, probably due to a phone keyboard"
            )
        return None
