import csv
import dataclasses
from typing import List, Dict, Optional

import tqdm
import requests

from e621_gallery_finder.e621_api import E621API
from e621_gallery_finder.post_issues import PostIssues
from e621_gallery_finder.source_checks import FAUserLink, FADirectLink, TwitterGallery, TwitterDirectLink, \
    FixableSourceMatch
from e621_source_cleanup.checks.base import BaseCheck
from e621_source_cleanup.main import setup_max_int, fetch_db_dump_path, csv_line_count


def post_to_url(site_id: str, post_id: str, username: Optional[str] = None) -> str:
    return {
        "e621": f"https://e621.net/posts/{post_id}/",
        "fa": f"https://www.furaffinity.net/view/{post_id}/",
        "twitter": f"https://twitter.com/{username or 'user'}/status/{post_id}"
    }[site_id]


def replace_prefix(source: str, old_prefix: str, new_prefix: str) -> str:
    if source.startswith(old_prefix):
        return new_prefix + source[len(old_prefix):]
    return source


def clean_direct_link(direct_link: Optional[str]) -> Optional[str]:
    if direct_link is None:
        return None
    direct_link = replace_prefix(direct_link, "http://", "https://")
    direct_link = replace_prefix(direct_link, "https://d.facdn.net/", "https://d.furaffinity.net/")
    direct_link = replace_prefix(direct_link, "https://d2.facdn.net/", "https://d.furaffinity.net/")
    return direct_link


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


def scan_csv(csv_path: str, checks: List[BaseCheck]) -> Dict[str, List[FixableSourceMatch]]:
    total_lines = csv_line_count(csv_path)
    match_dict = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in tqdm.tqdm(reader, desc="Checking sources", total=total_lines):
            if len(match_dict) >= 100:  # TODO: This is just for testing fix
                break
            post_id = row[0]
            sources = row[4]
            if not sources.strip():
                continue
            source_list = [s.strip() for s in sources.strip().split("\n")]
            all_matches = []
            for check in checks:
                try:
                    matches = check.matches(source_list, post_id)
                except Exception as e:
                    print(f"CHECK FAILURE. {check.name} failed to check {post_id}")
                    raise e
                if matches:
                    all_matches.extend(matches)
            if all_matches:
                match_dict[post_id] = all_matches
                # print(f"Found {len(all_matches)} source match: {all_matches}")
    return match_dict


class PostFixer:
    hash_priority = [
        "python:phash",
        "rust:dhash",
        "python:dhash",
        "python:whash",
        "python:ahash",
        "any:md5",
        "any:sha256",
    ]
    _hash_id_priority = None

    def __init__(self, e6_api: "E621API") -> None:
        self.api = e6_api

    @property
    def hash_id_priority(self) -> List[int]:
        if self._hash_id_priority is not None:
            return self._hash_id_priority
        hash_algos = requests.get("https://faexportdb.spangle.org.uk/api/hash_algos.json").json()
        id_priority = []
        for algo_name in self.hash_priority:
            found = False
            for algo_data in hash_algos["data"]["hash_algos"]:
                if f"{algo_data['language']}:{algo_data['algorithm_name']}" == algo_name:
                    id_priority.append(algo_data["algo_id"])
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not find hash by name {algo_name}")
        self._hash_id_priority = id_priority
        return id_priority

    def find_matching_source(self, post_id: str, post_issues: PostIssues) -> List[NewSource]:
        faxdb_post_data = requests.get(
            f"https://faexportdb.spangle.org.uk/api/view/submissions/e621/{post_id}.json"
        ).json()
        post_hashes = faxdb_post_data["data"]["submission_data"]["files"][0]["file_hashes"]
        remaining_match_infos = post_issues.unique_match_info()
        new_sources = []
        e6_link = post_to_url("e621", post_id)
        for hash_id in self.hash_id_priority:
            value = next(iter(
                [file_hash["hash_value"] for file_hash in post_hashes if file_hash["algo_id"] == hash_id]
            ), None)
            if not value:
                continue
            matching_results = requests.post(
                "https://faexportdb.spangle.org.uk/api/hash_search/",
                json={
                    "algo_id": hash_id,
                    "hash_value": value,
                }
            ).json()
            for snapshot in matching_results["results"]:
                if snapshot["website_id"] == "e621":
                    if snapshot["site_submission_id"] == post_id:
                        # Tautologically true self-match
                        continue
                    other_e6_link = post_to_url("e621", snapshot["site_submission_id"])
                    print(f"Another post ({other_e6_link}) on e621 matches hash of post: {e6_link}")
                    continue
                for match_info in remaining_match_infos[:]:
                    if match_info.might_match_snapshot(snapshot):
                        remaining_match_infos.remove(match_info)
                        new_source = NewSource.from_snapshot(snapshot, match_info.site_user_id)
                        new_sources.append(new_source)
                        print(f"Found a potential source for post: {e6_link}, {new_source.submission_link}")
        if remaining_match_infos:
            print(f"Can't find any matches for post {e6_link}")
        return new_sources

    def fix_sources(self, match_dict: Dict[str, List[FixableSourceMatch]]) -> None:
        for post_id, matches in match_dict.items():
            post_issues = PostIssues(matches)
            new_sources = self.find_matching_source(post_id, post_issues)
            if new_sources:
                all_new_sources = sum([new_source.source_links() for new_source in new_sources], start=[])
                self.api.add_new_sources(post_id, all_new_sources)


if __name__ == "__main__":
    setup_max_int()
    path = fetch_db_dump_path()
    checkers = [
        FAUserLink(),
        FADirectLink(),
        TwitterGallery(),
        TwitterDirectLink(),
    ]
    m_dict = scan_csv(path, checkers)
    api = E621API(
        "e621_gallery_finder/1.0.0 (by dr-spangle on e621)",
        "dr-spangle",
        ""
    )
    fixer = PostFixer(api)
    fixer.fix_sources(m_dict)

