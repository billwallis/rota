select
    member_name,
    last_actioned
from rota_members
order by
    last_actioned,
    member_name
