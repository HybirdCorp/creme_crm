from .campaign_emails_send import campaign_emails_send_type
from .entity_emails_send import entity_emails_send_type
from .entity_emails_sync import entity_emails_sync_type

jobs = (
    campaign_emails_send_type,
    entity_emails_send_type,
    entity_emails_sync_type,
)
