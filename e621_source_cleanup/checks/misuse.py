import string
from typing import Optional, List

from e621_source_cleanup.checks.base import SourceMatch, StringCheck


class CommaCheck(StringCheck):

    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        if ", " not in source:
            return None
        source_split = source.split(", ")
        for source_part in source_split:
            if " " in source_part:
                return None
        return SourceMatch(
            post_id,
            source,
            None,
            self,
            "Having a comma in the source indicates it's probably formatted wrong"
        )


class TagsCheck(StringCheck):

    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        if " " not in source:
            return None
        if "," in source:
            return None
        if len(source) < 70:
            return None
        split_words = source.split(" ")
        for word in split_words:
            if word.lower() != word:
                return None
        return SourceMatch(
            post_id,
            source,
            None,
            self,
            "Looks like this source might be a list of tags?"
        )


class TextCheck(StringCheck):

    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        if " " not in source:
            return None
        if len(source) < 50:
            return None
        return SourceMatch(
            post_id,
            source,
            None,
            self,
            "Seems like this source is just a message, maybe?"
        )


class EmailCheck(StringCheck):

    def matches_str(self, source: str, post_id: str) -> Optional[SourceMatch]:
        if "@" in source:
            return SourceMatch(
                post_id,
                source,
                None,
                self,
                "Email address listed in sources, alongside non-email sources"
            )
        return None

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[SourceMatch]]:
        matches = super().matches(source_list, post_id)
        if matches and len(source_list) > len(matches):
            return matches
        return []
