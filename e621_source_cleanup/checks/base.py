import dataclasses
from abc import ABC, abstractmethod
from typing import List, Optional, Type


@dataclasses.dataclass
class SourceURL:
    protocol: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    raw: str

    @property
    def domain_clean(self) -> Optional[str]:
        if not self.domain:
            return None
        if self.domain.startswith("www."):
            return self.domain[4:]
        return self.domain

    @classmethod
    def decompose_source(cls, source_link: str) -> Optional["SourceURL"]:
        raw = source_link
        protocol = None
        if "://" in source_link:
            protocol, source_link = source_link.split("://", 1)
        domain = None
        path = None
        if "/" in source_link:
            domain, path = source_link.split("/", 1)
        return SourceURL(
            protocol,
            domain,
            path,
            raw
        )


@dataclasses.dataclass
class SourceMatch:
    post_id: str
    source: str
    replacement: Optional[str]
    check: Type["BaseCheck"]
    reason: str


class BaseCheck(ABC):

    @abstractmethod
    def matches(self, source_list: List[str], post_id: str) -> Optional[List[SourceMatch]]:
        pass


class StringCheck(BaseCheck):

    @abstractmethod
    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        pass

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[SourceMatch]]:
        matches = []
        for source in source_list:
            if match := self.matches_str(source, post_id):
                matches.append(match)
        return matches


class URLCheck(StringCheck):

    @abstractmethod
    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        pass

    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        source_url = SourceURL.decompose_source(source)
        source_domain = source_url.domain
        if source_domain is None:
            return None
        if match := self.matches_url(source_url, post_id):
            return match
        return None
