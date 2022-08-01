import csv
import glob
import gzip
import json
import os
import re
import shutil
import sys
from collections import Counter
from typing import List, Dict

import requests
import tqdm

from e621_source_cleanup.checks.base import BaseCheck, SourceMatch
from e621_source_cleanup.checks.formatting import SpacesInURL
from e621_source_cleanup.checks.furaffinity import CommentsLink, OldCDN, UserLinkWithoutSubmission, \
    DirectLinkWithoutSubmission, BrokenCDN
from e621_source_cleanup.checks.misuse import CommaCheck, TagsCheck, TextCheck, EmailCheck, LocalPath
from e621_source_cleanup.checks.protocols import MissingProtocol, BrokenProtocols, UnknownProtocol, InsecureProtocol
from e621_source_cleanup.checks.twitter import TwitFixCheck, TwitterTracking

DB_DUMP_DIR = "db_export"


def setup_max_int() -> None:
    # Set up field size limit to be able to handle e621 data dumps
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)


def csv_line_count(csv_path: str) -> int:
    cache_file = csv_path + ".line_count"
    try:
        with open(cache_file, "r") as f:
            return int(f.read())
    except FileNotFoundError:
        pass
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        line_count = sum([1 for _ in tqdm.tqdm(reader)]) - 1  # Remove header line
    with open(cache_file, "w") as f:
        f.write(str(line_count))
    return line_count


def scan_csv(csv_path: str, checks: List[BaseCheck]) -> Dict[str, List[SourceMatch]]:
    total_lines = csv_line_count(csv_path)
    match_dict = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in tqdm.tqdm(reader, desc="Checking sources", total=total_lines):
            post_id = row[0]
            sources = row[4]
            if not sources.strip():
                continue
            source_list = [s.strip() for s in sources.strip().split("\n")]
            all_matches = []
            for check in checks:
                if matches := check.matches(source_list, post_id):
                    all_matches.extend(matches)
            if all_matches:
                match_dict[post_id] = all_matches
                # print(f"Found {len(all_matches)} source match: {all_matches}")
    return match_dict


def generate_report(csv_path: str, checks: List[BaseCheck], match_dict: Dict[str, List[SourceMatch]]) -> None:
    total_lines = csv_line_count(csv_path)
    print(f"There are {total_lines} posts in the dataset")
    print(f"{len(match_dict)} posts have sources matching at least one check")
    # Build by_check dict
    by_check = {
        chk: {
            "total": [],
            "auto": []
        }
        for chk in checks
    }
    for matches in match_dict.values():
        for match in matches:
            by_check[match.check]["total"].append(match)
            if match.replacement:
                by_check[match.check]["auto"].append(match)
    # Print totals by check
    print("Total by check")
    check_counter = Counter({chk: len(matches["total"]) for chk, matches in by_check.items()})
    for chk, match_count in check_counter.most_common():
        solvable = len(by_check[chk]["auto"])
        percent = solvable / match_count * 100
        print(f"- {chk.name}: Total: {match_count}. Solvable: {solvable} ({percent:02f}%)")
    # Print total errors, total solvable
    print(f"Total errors: {sum(len(by_check[chk]['total']) for chk in checks)}")
    print(f"Total solvable errors: {sum(len(by_check[chk]['auto']) for chk in checks)}")
    # Print check reports
    for chk, matches in by_check.items():
        check_report = chk.report()
        if check_report:
            print(f"## Report by {chk.name}:")
            print(check_report)
    # Save data as json
    json_data = {
        post_id: [match.to_json() for match in matches]
        for post_id, matches in match_dict.items()
    }
    with open(f"{csv_path}.results.json", "w") as f:
        json.dump(json_data, f, indent=2)


def fetch_db_dump_path() -> str:
    os.makedirs(DB_DUMP_DIR, exist_ok=True)
    files = glob.glob(f"{DB_DUMP_DIR}/*.csv")
    if files:
        return sorted(files)[-1]
    dump_listing = requests.get("https://e621.net/db_export/").content.decode("utf-8")
    dump_link_regex = re.compile(r"<a href=\"(posts-\d{4}-\d{2}-\d{2}.csv.gz)\">")
    dump_matches = [match.group(1) for match in dump_link_regex.finditer(dump_listing)]
    last_dump = sorted(dump_matches)[-1]
    print(f"Downloading dump: {last_dump}")
    dump_url = f"https://e621.net/db_export/{last_dump}"
    response = requests.get(dump_url, stream=True)
    with open(f"{DB_DUMP_DIR}/{last_dump}", "wb+") as handle:
        for data in tqdm.tqdm(response.iter_content(10_000), unit_scale=10, unit="kb"):
            handle.write(data)
    print("Decompressing database dump")
    last_dump_csv = last_dump[:-3]
    with gzip.open(f"{DB_DUMP_DIR}/{last_dump}", "rb") as f_in:
        with open(f"{DB_DUMP_DIR}/{last_dump_csv}", "wb+") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return f"{DB_DUMP_DIR}/{last_dump_csv}"


if __name__ == "__main__":
    setup_max_int()
    path = fetch_db_dump_path()
    checkers = [
        TwitFixCheck(),
        TwitterTracking(),
        CommentsLink(),
        CommaCheck(),
        OldCDN(),
        BrokenCDN(),
        UserLinkWithoutSubmission(),
        DirectLinkWithoutSubmission(),
        TagsCheck(),
        TextCheck(),
        EmailCheck(),
        LocalPath(),
        MissingProtocol(),
        BrokenProtocols(),
        UnknownProtocol(),
        InsecureProtocol(),
        SpacesInURL(),
    ]
    match_result = scan_csv(path, checkers)
    generate_report(path, checkers, match_result)

