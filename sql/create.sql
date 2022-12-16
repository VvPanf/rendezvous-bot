drop table if exists rendezvous;
drop table if exists users;

create table if not exists users (
    id serial not null primary key,
    user_id integer,
    state integer default 0
);

create unique index if not exists user_id_index on users(user_id);

create table if not exists rendezvous (
    id serial not null primary key,
    first_person integer not null,
    second_person integer not null,
    plan varchar(1024),
    stage_count int,
    current_stage int,
    foreign key (first_person) references users (id) on delete cascade,
    foreign key (second_person) references users (id) on delete cascade
);

create index if not exists first_index on rendezvous(first_person);
create index if not exists second__index on rendezvous(second_person);