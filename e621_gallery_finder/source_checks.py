from abc import abstractmethod
from typing import List, Optional

from e621_gallery_finder.main import FixableSourceMatch, MatchInfo
from e621_source_cleanup.checks.base import BaseCheck, SourceURL


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
