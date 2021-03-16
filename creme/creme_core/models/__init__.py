# -*- coding: utf-8 -*-

from django.conf import settings

from .auth import (  # NOQA
    CremeUser,
    EntityCredentials,
    Sandbox,
    SetCredentials,
    UserRole,
)
from .base import CremeModel  # NOQA
from .bricks import *  # NOQA
from .button_menu import ButtonMenuItem  # NOQA
from .creme_property import CremeProperty, CremePropertyType  # NOQA
from .currency import Currency  # NOQA
from .custom_field import *  # NOQA
from .custom_form import CustomFormConfigItem  # NOQA
from .database import CaseSensitivity  # NOQA
from .deletion import (  # NOQA
    CREME_REPLACE,
    CREME_REPLACE_NULL,
    DeletionCommand,
    TrashCleaningCommand,
)
from .entity import CremeEntity  # NOQA
from .entity_filter import EntityFilter, EntityFilterCondition  # NOQA
from .fields_config import FieldsConfig  # NOQA
from .file_ref import FileRef  # NOQA
from .header_filter import HeaderFilter  # NOQA
from .history import HistoryConfigItem, HistoryLine  # NOQA
from .i18n import Language  # NOQA
from .imprint import Imprint  # NOQA
from .job import EntityJobResult, Job, JobResult, MassImportJobResult  # NOQA
from .lock import Mutex, MutexAutoLock  # NOQA
from .menu import MenuConfigItem  # NOQA
from .relation import Relation, RelationType, SemiFixedRelationType  # NOQA
from .reminder import DateReminder  # NOQA
from .search import SearchConfigItem  # NOQA
from .setting_value import SettingValue  # NOQA
from .vat import Vat  # NOQA
from .version import Version  # NOQA

if settings.TESTS_ON:
    from creme.creme_core.tests.fake_models import *  # NOQA
del settings
