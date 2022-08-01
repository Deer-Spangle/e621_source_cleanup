import string
from typing import List, Optional

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
            self.__class__,
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
            self.__class__,
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
            self.__class__,
            "Seems like this source is just a message, maybe?"
        )
