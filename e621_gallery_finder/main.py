import csv
from typing import List, Dict

import tqdm
import requests

from e621_gallery_finder.source_checks import FAUserLink, FADirectLink, TwitterGallery, TwitterDirectLink, \
    FixableSourceMatch
from e621_source_cleanup.checks.base import BaseCheck, SourceMatch
from e621_source_cleanup.main import setup_max_int, fetch_db_dump_path, csv_line_count


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

