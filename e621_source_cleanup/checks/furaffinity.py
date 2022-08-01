from typing import Optional, List

from e621_source_cleanup.checks.base import URLCheck, SourceURL, SourceMatch, BaseCheck


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


class UserLinkWithoutSubmission(BaseCheck):

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[SourceMatch]]:
        fa_user_source = None
        has_fa_submission_source = False
        for source in source_list:
            source_url = SourceURL.decompose_source(source)
            if source_url.domain_clean is not "furaffinity.net":
                continue
            if any(source_url.path.startswith(prefix) for prefix in ["user/", "gallery/", "scraps/"]):
                fa_user_source = source_url.raw
            if source_url.path.startswith("view/"):
                has_fa_submission_source = True
        if fa_user_source is not None and not has_fa_submission_source:
            return [SourceMatch(
                post_id,
                fa_user_source,
                None,
                self,
                "Post has a link to an FA user, but not a link to the specific submission"
            )]
        return []


class DirectLinkWithoutSubmission(BaseCheck):

    def __init__(self) -> None:
        super().__init__()
        self.cdn_domains = {
            "d.facdn.net",
            "d2.facdn.net",
            "d.furaffinity.net",
        }

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[SourceMatch]]:
        fa_direct_link = None
        has_fa_submission_source = False
        for source in source_list:
            source_url = SourceURL.decompose_source(source)
            if source_url.domain_clean is "furaffinity.net" and source_url.path.startswith("view/"):
                has_fa_submission_source = True
            if source_url.domain in self.cdn_domains:
                fa_direct_link = source_url.raw
        if fa_direct_link is not None and not has_fa_submission_source:
            return [SourceMatch(
                post_id,
                fa_direct_link,
                None,
                self,
                "Post has a direct link to an image on FA, but not to the submission page"
            )]
        return []
