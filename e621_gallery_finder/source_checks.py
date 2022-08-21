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


@dataclasses.dataclass
class PostIssues:
    source_issues: List[FixableSourceMatch]

    @property
    def all_match_info(self) -> List[MatchInfo]:
        return sum([source_issue.imprecise_matches for source_issue in self.source_issues], start=[])

    def unique_match_info_by_site(self) -> Dict[str, List[MatchInfo]]:
        match_dict = {}
        for match_info in self.all_match_info:
            if match_info.site_id not in match_dict:
                match_dict[match_info.site_id] = []
            match_dict[match_info.site_id].append(match_info)

        unique_site_dict = {}
        for site_id, site_match_infos in match_dict.items():
            username_known: Dict[str, MatchInfo] = {}
            direct_only: Dict[str, MatchInfo] = {}
            only_site: Optional[MatchInfo] = None
            for match_info in site_match_infos:
                if match_info.site_user_id is None:
                    if match_info.direct_image_link is None:
                        only_site = match_info
                    else:
                        direct_only[match_info.direct_image_link] = match_info
                else:
                    if match_info.site_user_id not in username_known:
                        username_known[match_info.site_user_id] = match_info
                    else:
                        if match_info.direct_image_link is not None:
                            username_known[match_info.site_user_id] = match_info
            site_matches = list(username_known.values())
            username_known_direct_links = [match_info.direct_image_link for match_info in username_known.values()]
            for match_info in direct_only.values():
                if match_info.direct_image_link not in username_known_direct_links:
                    site_matches.append(match_info)
            if not site_matches and only_site:
                site_matches.append(only_site)
            unique_site_dict[site_id] = site_matches
        return unique_site_dict

    def unique_match_info(self) -> List[MatchInfo]:
        return sum(self.unique_match_info_by_site().values(), start=[])


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
