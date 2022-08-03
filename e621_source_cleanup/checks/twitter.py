from typing import Optional

from e621_source_cleanup.checks.base import SourceURL, SourceMatch, URLCheck


class TwitFixCheck(URLCheck):
    def __init__(self):
        self.twitfix_domains = [
            "vxtwitter.com",
            "ayytwitter.com",
            "fxtwitter.com",
            "pxtwitter.com",
            "twitter64.com",
            "twittpr.com",
            "nitter.net",
        ]

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        source_domain = source_url.domain_clean
        if source_domain is None:
            return None
        if source_domain in self.twitfix_domains:
            return SourceMatch(
                post_id,
                source_url.raw,
                f"https://twitter.com/{source_url.path}",
                self,
                f"TwitFix domain {source_domain} changed to direct twitter link"
            )


class TwitterTracking(TwitFixCheck):

    def __init__(self):
        super().__init__()
        self.twitter_urls = self.twitfix_domains + ["twitter.com"]

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if not source_url.path:
            return None
        if source_url.domain_clean not in self.twitter_urls:
            return None
        if "?" not in source_url.path:
            return None
        cleaned_path, _ = source_url.path.split("?", 1)
        return SourceMatch(
            post_id,
            source_url.raw,
            f"https://twitter.com/{cleaned_path}",
            self,
            "Twitter link had tracking info attached"
        )


class OldDirectURL(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain != "pbs.twimg.com":
            return None
        params = {}
        if ":" in source_url.path:
            path, name = source_url.path.split(":", 1)
            params["name"] = name
            if "?format=" in path:
                return None  # Link is malformed, let the malformed link check take it
            if "?format=" in name:
                name, ext = name.split("?format=")
            else:
                path, ext = path.split(".", 1)
            params["format"] = ext
            fix_url = f"https://{source_url.domain}/{path}?" + "&".join(f"{key}={val}" for key, val in params.items())
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Old twitter direct image link format"
            )
        if "." in source_url.path:
            path, ext_args = source_url.path.split(".", 1)
            if "?" not in ext_args:
                return None
            ext, args = ext_args.split("?", 1)
            path = f"{path}?format={ext}&{args}"
            fix_url = f"https://{source_url.domain}/{path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Old twitter direct image link format"
            )
        return None


class MalformedDirectLinks(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        # Some links have been malformed as ?format=jpg&name=orig?name=orig, by a previous source fixer.
        if source_url.domain != "pbs.twimg.com":
            return None
        if "?name=" in source_url.path and "?format=" in source_url.path:
            path, _ = source_url.path.split("?name=", 1)
            fix_url = f"https://{source_url.domain}/{path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Correcting twitter direct image link malformed by a previous bot"
            )
        if "?format=" in source_url.path and source_url.path.endswith("&name="):
            path, args = source_url.path.split("?format=", 1)
            args = args[:-6]
            fix_url = None
            if ":" in args:
                arg_format, arg_name = args.split(":", 1)
                fix_url = f"https://{source_url.domain}/{path}?format={arg_format}&name={arg_name}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Correct twitter direct image link malformed by a previous bot"
            )


class MobileLink(URLCheck):

    def matches_url(self, source_url: SourceURL, post_id: str) -> Optional[SourceMatch]:
        if source_url.domain == "mobile.twitter.com":
            fix_url = f"https://twitter.com/{source_url.path}"
            return SourceMatch(
                post_id,
                source_url.raw,
                fix_url,
                self,
                "Switch mobile.twitter.com links to direct twitter.com ones"
            )
        return None
