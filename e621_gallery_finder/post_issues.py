import dataclasses
from typing import List, Dict, Optional

from e621_gallery_finder.source_checks import FixableSourceMatch, MatchInfo


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
