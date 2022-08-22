import dataclasses
from typing import Optional, List, Dict

from e621_gallery_finder.main import post_to_url, clean_direct_link


@dataclasses.dataclass
class NewSource:
    submission_link: str
    direct_link: Optional[str]

    def source_links(self) -> List[str]:
        new_sources = [self.submission_link]
        if self.direct_link is not None:
            new_sources.append(self.direct_link)
        return new_sources

    @classmethod
    def from_snapshot(cls, snapshot: Dict, suspected_username: Optional[str] = None) -> "NewSource":
        submission_url = post_to_url(snapshot['website_id'], snapshot['site_submission_id'], suspected_username)
        direct_link = clean_direct_link(snapshot["submission_data"]["files"][0]["file_url"])
        return cls(submission_url, direct_link)
