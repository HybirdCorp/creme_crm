from .temp_files_cleaner import temp_files_cleaner_type
from .deletor import deletor_type
from .batch_process import batch_process_type
from .mass_import import mass_import_type
from .reminder import reminder_type


jobs = (
    temp_files_cleaner_type,
    deletor_type,
    batch_process_type,
    mass_import_type,
    reminder_type,
)
