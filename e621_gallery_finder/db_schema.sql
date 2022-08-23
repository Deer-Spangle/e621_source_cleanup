
CREATE TABLE IF NOT EXISTS post_status (
    post_id str not null,
    skip_date date,
    last_checked date
);

CREATE UNIQUE INDEX IF NOT EXISTS post_status_post_id
    ON post_status (post_id);

CREATE TABLE IF NOT EXISTS post_new_sources (
    source_id integer
        constraint table_name_pk
            primary key autoincrement,
    post_id str not null,
    submission_link str,
    direct_link str,
    checked bool not null default false,
    approved bool
);

