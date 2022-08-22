import datetime
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Cursor
from typing import Optional, Union, Tuple, Dict, ContextManager, List


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
