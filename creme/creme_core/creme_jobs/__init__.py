from .batch_process import batch_process_type
from .deletor import deletor_type
from .mass_import import mass_import_type
from .notification_emails_sender import notification_emails_sender_type
from .reminder import reminder_type
from .session_cleaner import sessions_cleaner_type
from .temp_files_cleaner import temp_files_cleaner_type
from .trash_cleaner import trash_cleaner_type

jobs = (
    temp_files_cleaner_type,
    deletor_type,
    trash_cleaner_type,
    batch_process_type,
    mass_import_type,
    notification_emails_sender_type,
    reminder_type,
    sessions_cleaner_type,
)
