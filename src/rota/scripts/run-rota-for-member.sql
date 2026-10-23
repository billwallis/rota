/* TODO: Should we throw an error on unrecognised members instead? */
insert into rota_members (member_name, last_actioned)
values (:member_name, :actioned_at)
on conflict (member_name) do update
    set last_actioned = :actioned_at
;

insert into rota_log (member_name, action)
values (:member_name, 'ran rota')
;
