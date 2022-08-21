import dataclasses
from abc import abstractmethod
from typing import List, Optional, Dict

from e621_source_cleanup.checks.base import BaseCheck, SourceURL, SourceMatch


@dataclasses.dataclass
class MatchInfo:
    source: SourceURL
    e621_post_id: str
    site_id: str
    site_user_id: Optional[str] = None
    direct_image_link: Optional[str] = None

    def might_match_snapshot(self, snapshot: Dict) -> bool:
        if snapshot["website_id"] != self.site_id:
            return False
        uploader_id = snapshot["submission_data"]["uploader_site_user_id"]
        if self.site_user_id is not None and uploader_id is not None and self.site_user_id != uploader_id:
            return False
        file_urls = [file["file_url"] for file in snapshot["submission_data"]["files"] if file["file_url"] is not None]
        if self.direct_image_link is not None and file_urls and self.direct_image_link not in file_urls:
            return False
        return True


@dataclasses.dataclass
class FixableSourceMatch(SourceMatch):
    imprecise_matches: List[MatchInfo]

    def match_snapshot(self, snapshot: Dict) -> bool:
        return all(match_info.might_match_snapshot(snapshot) for match_info in self.imprecise_matches)


class IncompleteSourceCheck(BaseCheck):

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[FixableSourceMatch]]:
        imprecise_matches = []
        has_precise_match = False
        for source in source_list:
            source_url = SourceURL.decompose_source(source)
            if match := self.imprecise_match(source_url, post_id):
                imprecise_matches.append(match)
            if self.is_precise_match(source_url, post_id):
                has_precise_match = True
        if imprecise_matches and not has_precise_match:
            return [FixableSourceMatch(
                post_id,
                imprecise_matches[0].source.raw,
                None,
                self,
                "Post has an imprecise match, but no precise match.",
                imprecise_matches
            )]
        return []

    @abstractmethod
    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        pass

    @abstractmethod
    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        pass


class FAUserLink(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean != "furaffinity.net":
            return None
        if any(source.path.startswith(prefix) for prefix in ["user/", "gallery/", "scraps/"]):
            username = source.path.split("/")[1]
            return MatchInfo(
                source,
                post_id,
                "fa",
                site_user_id=username
            )

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "furaffinity.net":
            return False
        return source.path.startswith("view/")


class FADirectLink(IncompleteSourceCheck):

    def __init__(self) -> None:
        super().__init__()
        self.cdn_domains = {
            "d.facdn.net",
            "d2.facdn.net",
            "d.furaffinity.net",
        }

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain in self.cdn_domains:
            username = source.path.split("/")[1]
            return MatchInfo(
                source,
                post_id,
                "fa",
                site_user_id=username,
                direct_image_link=source.raw,
            )
        pass

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "furaffinity.net":
            return False
        return source.path.startswith("view/")


class TwitterGallery(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean != "twitter.com":
            return None
        if source.path.count("/") < 2:
            username = source.path.split("/")[0]
            return MatchInfo(
                source,
                post_id,
                "twitter",
                site_user_id=username
            )
        return None

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "twitter.com":
            return False
        return "/status/" in source.path


class TwitterDirectLink(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean == "pbs.twimg.com":
            return MatchInfo(
                source,
                post_id,
                "twitter",
                direct_image_link=source.raw,
            )
        return None

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "twitter.com":
            return False
        return "/status/" in source.path
