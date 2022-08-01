import dataclasses
from abc import ABC, abstractmethod
from typing import List, Optional, Type


@dataclasses.dataclass
class SourceURL:
    protocol: Optional[str]
    domain: Optional[str]
    path: Optional[str]
    raw: str

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
    def matches(self, source_list: List[str], post_id: str) -> bool:
        pass
