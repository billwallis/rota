insert into rota_members (member_name)
values (:member_name)
;

insert into rota_log (member_name, action)
values (:member_name, 'created')
;
