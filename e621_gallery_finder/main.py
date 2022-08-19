import csv
import dataclasses
from abc import abstractmethod
from typing import Optional, List, Dict

import tqdm
import requests

from e621_source_cleanup.checks.base import BaseCheck, SourceURL, SourceMatch
from e621_source_cleanup.main import setup_max_int, fetch_db_dump_path, csv_line_count


@dataclasses.dataclass
class MatchInfo:
    source: SourceURL
    e621_post_id: str
    site_id: str
    site_user_id: Optional[str] = None
    direct_image_link: Optional[str] = None

    def might_match_snapshot(self, snapshot: Dict) -> bool:
        if snapshot["website_id"] != self.site_id:
            return False
        uploader_id = snapshot["submission_data"]["uploader_site_user_id"]
        if self.site_user_id is not None and uploader_id is not None and self.site_user_id != uploader_id:
            return False
        file_urls = [file["file_url"] for file in snapshot["submission_data"]["files"] if file["file_url"] is not None]
        if self.direct_image_link is not None and file_urls and self.direct_image_link not in file_urls:
            return False
        return True


@dataclasses.dataclass
class FixableSourceMatch(SourceMatch):
    imprecise_matches: List[MatchInfo]

    def match_snapshot(self, snapshot: Dict) -> bool:
        return all(match_info.might_match_snapshot(snapshot) for match_info in self.imprecise_matches)


class IncompleteSourceCheck(BaseCheck):

    def matches(self, source_list: List[str], post_id: str) -> Optional[List[FixableSourceMatch]]:
        imprecise_matches = []
        has_precise_match = False
        for source in source_list:
            source_url = SourceURL.decompose_source(source)
            if match := self.imprecise_match(source_url, post_id):
                imprecise_matches.append(match)
            if self.is_precise_match(source_url, post_id):
                has_precise_match = True
        if imprecise_matches and not has_precise_match:
            return [FixableSourceMatch(
                post_id,
                imprecise_matches[0].source.raw,
                None,
                self,
                "Post has an imprecise match, but no precise match.",
                imprecise_matches
            )]
        return []

    @abstractmethod
    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        pass

    @abstractmethod
    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        pass


class FAUserLink(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean != "furaffinity.net":
            return None
        if any(source.path.startswith(prefix) for prefix in ["user/", "gallery/", "scraps/"]):
            username = source.path.split("/")[1]
            return MatchInfo(
                source,
                post_id,
                "fa",
                site_user_id=username
            )

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "furaffinity.net":
            return False
        return source.path.startswith("view/")


class FADirectLink(IncompleteSourceCheck):

    def __init__(self) -> None:
        super().__init__()
        self.cdn_domains = {
            "d.facdn.net",
            "d2.facdn.net",
            "d.furaffinity.net",
        }

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain in self.cdn_domains:
            username = source.path.split("/")[1]
            return MatchInfo(
                source,
                post_id,
                "fa",
                site_user_id=username,
                direct_image_link=source.raw,
            )
        pass

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "furaffinity.net":
            return False
        return source.path.startswith("view/")


class TwitterGallery(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean != "twitter.com":
            return None
        if source.path.count("/") < 2:
            username = source.path.split("/")[0]
            return MatchInfo(
                source,
                post_id,
                "twitter",
                site_user_id=username
            )
        return None

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "twitter.com":
            return False
        return "/status/" in source.path


class TwitterDirectLink(IncompleteSourceCheck):

    def imprecise_match(self, source: SourceURL, post_id: str) -> Optional[MatchInfo]:
        if source.domain_clean == "pbs.twimg.com":
            return MatchInfo(
                source,
                post_id,
                "twitter",
                direct_image_link=source.raw,
            )
        return None

    def is_precise_match(self, source: SourceURL, post_id: str) -> bool:
        if source.domain_clean != "twitter.com":
            return False
        return "/status/" in source.path


def scan_csv(csv_path: str, checks: List[BaseCheck]) -> Dict[str, List[SourceMatch]]:
    total_lines = csv_line_count(csv_path)
    match_dict = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in tqdm.tqdm(reader, desc="Checking sources", total=total_lines):
            if len(match_dict) >= 50:  # TODO: This is just for testing fix
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

hash_priority = [
    "python:phash",
    "rust:dhash",
    "python:dhash",
    "python:whash",
    "python:ahash",
    "any:md5",
    "any:sha256",
]


def get_hash_id_priority() -> List[int]:
    hash_algos = requests.get("https://faexportdb.spangle.org.uk/api/hash_algos.json").json()
    id_priority = []
    for algo_name in hash_priority:
        found = False
        for algo_data in hash_algos["data"]["hash_algos"]:
            if f"{algo_data['language']}:{algo_data['algorithm_name']}" == algo_name:
                id_priority.append(algo_data["algo_id"])
                found = True
                break
        if not found:
            raise ValueError(f"Could not find hash by name {algo_name}")
    return id_priority


def find_matching_source(post_id: str, matches: List[FixableSourceMatch], id_priority: List[int]) -> None:
    faxdb_post_data = requests.get(
        f"https://faexportdb.spangle.org.uk/api/view/submissions/e621/{post_id}.json"
    ).json()
    post_hashes = faxdb_post_data["data"]["submission_data"]["files"][0]["file_hashes"]
    found = False
    for hash_id in id_priority:
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
                print(f"Another post ({snapshot['site_submission_id']}) on e621 matches hash of post: {post_id}")
                continue
            for fixable_match in matches:
                if fixable_match.match_snapshot(snapshot):
                    found = True
                    print(f"Found a potential source for post: {post_id}, Site: {snapshot['website_id']} & ID: {snapshot['site_submission_id']}")
    if not found:
        print(f"Can't find a match for post {post_id}")
    return None


def fix_sources(match_dict: Dict[str, List[FixableSourceMatch]]) -> None:
    id_priority = get_hash_id_priority()
    for post_id, matches in match_dict.items():
        find_matching_source(post_id, matches, id_priority)


if __name__ == "__main__":
    setup_max_int()
    path = fetch_db_dump_path()
    checkers =[
        FAUserLink(),
        FADirectLink(),
        TwitterGallery(),
        TwitterDirectLink(),
    ]
    match_dict = scan_csv(path, checkers)
    fix_sources(match_dict)

