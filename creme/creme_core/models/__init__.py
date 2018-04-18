# -*- coding: utf-8 -*-

from .auth import CremeUser, EntityCredentials, UserRole, SetCredentials  # NOQA

from file_ref import FileRef  # NOQA

from .base import CremeModel, CremeAbstractEntity  # NOQA
from .entity import CremeEntity  # NOQA

from .setting_value import SettingValue  # NOQA

from .relation import RelationType, Relation, SemiFixedRelationType  # NOQA
from .creme_property import CremePropertyType, CremeProperty  # NOQA
from .custom_field import *

from .fields_config import FieldsConfig  # NOQA
from .header_filter import HeaderFilter  # NOQA
from .entity_filter import EntityFilter, EntityFilterCondition, EntityFilterVariable  # NOQA

from .lock import Mutex, MutexAutoLock  # NOQA

from .i18n import Language  # NOQA
from .currency import Currency  # NOQA
from .vat import Vat  # NOQA

from .bricks import *  # NOQA
from .prefered_menu import PreferedMenuItem  # NOQA
from .button_menu import ButtonMenuItem  # NOQA

from .reminder import DateReminder  # NOQA

from .history import HistoryLine, HistoryConfigItem  # NOQA
from .search import SearchConfigItem  # NOQA

from .job import Job, JobResult, EntityJobResult, MassImportJobResult  # NOQA

from .version import Version  # NOQA


from django.conf import settings
if settings.TESTS_ON:
    from creme.creme_core.tests.fake_models import *  # NOQA
