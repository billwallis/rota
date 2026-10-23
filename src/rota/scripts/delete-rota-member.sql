delete from rota_members
where member_name = :member_name
;

insert into rota_log (member_name, action)
values (:member_name, 'deleted')
;
