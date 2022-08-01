from typing import Optional, SupportsAbs
from e621_source_cleanup.checks.base import SourceMatch, SourceURL, URLCheck


class MissingProtocol(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.domain:
            return None
        if not source_url.protocol:
            return SourceMatch(
                post_id,
                source_url.raw,
                None,
                self,
                "No protocol specified on link"
            )
        return None


class BrokenProtocols(URLCheck):
    
    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.protocol is None:
            return None
        if source_url.protocol in ["ttp", "ttps"]:
            return SourceMatch(
                post_id,
                source_url.raw,
                "h" + source_url.raw,
                self,
                "Source URL is missing first character"
            )
        if source_url.protocol in ["tp", "tps"]:
            return SourceMatch(
                post_id,
                source_url.raw,
                "ht" + source_url.raw,
                self,
                "Source URL is missing first two chars"
            )
        if source_url.protocol in ["p", "ps"]:
            return SourceMatch(
                post_id,
                source_url.raw,
                "htt" + source_url.raw,
                self,
                "Source URL is missing three chars"
            )
        return None


class UnknownProtocol(URLCheck):
    
    def __init__(self) -> None:
        super().__init__()
        self.protocols = {"http", "https", "ftp"}
        self.broken_protocols = set()
        for protocol in self.protocols:
            self.broken_protocols.update([protocol[n:] for n in range(len(protocol))])
        self.all_protocols = self.protocols.union(self.broken_protocols)

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.protocol:
            return None
        if source_url.protocol not in self.all_protocols:
            return SourceMatch(
                post_id,
                source_url.raw,
                None,
                self,
                f"Unknown protocol on URL: {source_url.protocol}"
            )
        return None


class InsecureProtocol(URLCheck):

    def __init__(self) -> None:
        super().__init__()
        self.secure_domains = {
            "furaffinity.net",
            "weasyl.com",
            "twitter.com",
        }
    
    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.protocol:
            return None
        if source_url.protocol != "http":
            return None
        if source_url.domain_clean in self.secure_domains:
            secure_url = f"https://{source_url.domain}/{source_url.path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                secure_url,
                self,
                "Using http protocol in source URL when domain supports https"
            )
        return SourceMatch(
            post_id,
            source_url.raw,
            None,
            self,
            "Using http protocol in URL, unknown if domain supports https"
        )
