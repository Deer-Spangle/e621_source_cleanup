from collections import Counter
from typing import Optional
from e621_source_cleanup.checks.base import SourceMatch, SourceURL, URLCheck


class MissingProtocol(URLCheck):

    def __init__(self):
        self.known_domains = {
            "furaffinity.net": "https://",
            "t.me": "https://",
            "twitter.com": "https://",
            "patreon.com": "https://",
        }
        self.report_domains = []

    def protocol_for_domain(self, domain: str) -> Optional[str]:
        if domain.endswith(".tumblr.com"):
            return "https://"
        if domain.endswith(".deviantart.com"):
            return "https://"
        if domain in self.known_domains:
            return self.known_domains[domain]
        return None

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.domain:
            return None
        if not source_url.protocol:
            fix_url = None
            fix_protocol = self.protocol_for_domain(source_url.domain_clean)
            if fix_protocol:
                fix_url = fix_protocol + source_url.raw
            else:
                self.report_domains.append(source_url.domain_clean)
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "No protocol specified on link"
            )
        return None

    def report(self) -> Optional[str]:
        counter = Counter(self.report_domains)
        return "Domains without protocols seen: " + ", ".join(f"{domain}: {n}" for domain, n in counter.most_common())


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
        self.report_protocols = []

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.protocol:
            return None
        if source_url.protocol not in self.all_protocols:
            self.report_protocols.append(source_url.protocol)
            return SourceMatch(
                post_id,
                source_url.raw,
                None,
                self,
                f"Unknown protocol on URL: {source_url.protocol}"
            )
        return None

    def report(self) -> Optional[str]:
        counter = Counter(self.report_protocols)
        return "Unknown protocols: " + ", ".join(f"{domain}: {count}" for domain, count in counter.most_common())


class InsecureProtocol(URLCheck):

    def __init__(self) -> None:
        super().__init__()
        self.secure_domains = {
            "furaffinity.net",
            "weasyl.com",
            "twitter.com",
        }
        self.report_domains = []

    def is_secure_domain(self, domain: str) -> bool:
        if domain in self.secure_domains:
            return True
        if domain.endswith(".tumblr.com"):
            return True
        if domain.endswith(".deviantart.com"):
            return True
        return False
    
    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.protocol:
            return None
        if source_url.protocol != "http":
            return None
        if self.is_secure_domain(source_url.domain_clean):
            secure_url = f"https://{source_url.domain}/{source_url.path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                secure_url,
                self,
                "Using http protocol in source URL when domain supports https"
            )
        self.report_domains.append(source_url.domain_clean)
        return SourceMatch(
            post_id,
            source_url.raw,
            None,
            self,
            "Using http protocol in URL, unknown if domain supports https"
        )

    def report(self) -> Optional[str]:
        counter = Counter(self.report_domains)
        return "Other domains seen: " + ", ".join(f"{domain}: {count}" for domain, count in counter.most_common())
