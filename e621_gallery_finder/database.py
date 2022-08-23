import datetime
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Cursor
from typing import Optional, Union, Tuple, Dict, ContextManager, List


from e621_gallery_finder.new_source import NewSourceEntry, PostStatusEntry


class Database:
    DB_FILE = "e6_post_sources.sqlite"

    def __init__(self) -> None:
        self.conn = sqlite3.connect(self.DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_db()

    def _create_db(self) -> None:
        cur = self.conn.cursor()
        schema_file = Path(__file__).parent / "db_schema.sql"
        with open(schema_file, "r") as f:
            cur.executescript(f.read())
        self.conn.commit()

    @contextmanager
    def _execute(self, query: str, args: Optional[Union[Tuple, Dict]] = None) -> ContextManager[Cursor]:
        cur = self.conn.cursor()
        try:
            if args:
                result = cur.execute(query, args)
            else:
                result = cur.execute(query)
            self.conn.commit()
            yield result
        finally:
            cur.close()

    def _just_execute(self, query: str, args: Optional[Union[Tuple, Dict]] = None) -> None:
        with self._execute(query, args):
            pass

    def add_post(self, post_id: str, last_checked: datetime.datetime) -> None:
        self._just_execute(
            "INSERT INTO post_status (post_id, last_checked) "
            "VALUES (?, ?) "
            "ON CONFLICT (post_id) "
            "DO UPDATE SET last_checked=excluded.last_checked",
            (post_id, last_checked)
        )

    def add_new_source(self, post_id: str, submission_link: Optional[str], direct_link: Optional[str]) -> None:
        self._just_execute(
           "INSERT INTO post_new_sources (post_id, submission_link, direct_link) "
           "VALUES (?, ?, ?)",
            (post_id, submission_link, direct_link)
        )

    def count_unchecked_sources(self) -> int:
        with self._execute(
            "SELECT COUNT(*) FROM post_new_sources WHERE checked = False"
        ) as result:
            for row in result:
                return row[0]
    
    def count_total_sources(self) -> int:
        with self._execute(
            "SELECT COUNT(*) FROM post_new_sources"
        ) as result:
            for row in result:
                return row[0]

    def get_next_unchecked_source(self) -> Optional[Tuple[PostStatusEntry, List[NewSourceEntry]]]:
        post_id = None
        with self._execute(
            "SELECT sources.post_id "
            "FROM post_new_sources sources "
            "LEFT JOIN post_status posts ON posts.post_id = sources.post_id "
            "WHERE checked = false "
            "ORDER BY posts.skip_date ASC, posts.last_checked ASC"
        ) as post_select:
            for row in post_select:
                post_id = row[0]
                break
        if post_id is None:
            return None
        post_status = None
        with self._execute(
            "SELECT skip_date, last_checked FROM post_status WHERE post_id = ?", (post_id,)
        ) as post_result:
            for row in post_result:
                skip_date = None
                if row[0]:
                    skip_date = datetime.datetime.fromisoformat(row[0])
                post_status = PostStatusEntry(post_id, skip_date, datetime.datetime.fromisoformat(row[1]))
        new_sources = []
        with self._execute(
            "SELECT source_id, submission_link, direct_link, checked, approved FROM post_new_sources "
            "WHERE post_id = ? AND checked = False",
                (post_id,)
        ) as source_result:
            for row in source_result:
                new_sources.append(NewSourceEntry(
                    row[1], row[2], row[0], row[3], row[4]
                ))
        return row_data, new_sources

    def update_post_skip(self, post_id: str, skip_date: datetime.datetime) -> None:
        self._just_execute(
            "UPDATE post_status SET skip_date = ? WHERE post_id = ?",
            (skip_date, post_id)
        )

    def update_source_approved(self, source_id: int, approved: bool) -> None:
        self._just_execute(
            "UPDATE post_new_sources SET checked = True, approved = ? WHERE source_id = ?",
            (approved, source_id)
        )

    def get_source(self, source_id: int) -> Optional[NewSourceEntry]:
        with self._execute(
            "SELECT post_id, submission_link, direct_link, checked, approved FROM post_new_sources WHERE source_id = ?",
            (source_id,)
        ) as result:
            for row in result:
                return NewSourceEntry(
                    source_id,
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4]
                )
        return None
