create table if not exists rota_members (
    member_name text not null primary key,
    last_actioned text not null default ('1900-01-01 00:00:00')
)
strict
;

create table if not exists rota_log (
    log_id integer not null primary key autoincrement,
    log_ts text not null default (current_timestamp),
    member_name text not null,
    action text not null
)
strict
;
