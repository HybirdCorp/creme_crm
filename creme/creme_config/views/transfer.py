################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from collections import OrderedDict
from json import dumps as json_dump
from typing import Any

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_sameorigin

from creme.creme_core.auth import STAFF_PERM
from creme.creme_core.views import generic

from ..constants import ID_VERSION
from ..core.exporters import EXPORTERS
from ..forms.transfer import ImportForm


class ConfigExport(generic.CheckedView):
    permissions = STAFF_PERM
    registry = EXPORTERS

    def get_info(self) -> dict:
        # NB: we use an OrderedDict to keep this global order in our output file
        #     (it seems better to be sure that 'version' is at the beginning,
        #     like in a file header).
        info: dict[str, Any] = OrderedDict()
        # 2.2: 1.0
        # 2.3: 1.1/1.2 the models for search & custom-forms have changed.
        # 2.4: 1.3 RelationBrickItem.brick_id has been removed (use 'id' now).
        # 2.5: 1.4 InstanceBrickConfigItems are exported and imported if possible.
        # 2.6: 1.5
        #    - Use UUID instead of ID with:
        #       - CremePropertyType
        #       - RelationBrickItem
        #       - InstanceBrickConfigItem
        #       - CustomBrickConfigItem
        #    - Changes in the data for EntityFilterCondition of Relation
        #      (CT uses natural-key, the key "entity_uuid" became just "entity").
        #    - Notification channels added
        #    - Use UUID instead of name with UserRole.
        #    - "extra_data" in EntityFilter/HeaderFilter.
        #    - UUID given for CustomFieldEnumValue.
        # 2.7: 1.6
        #    - The cells for RelationBrickItem are now stored as a dictionary.
        #    - Fields "role" & "superuser" for ButtonMenuItem.
        #    - Users are referenced by their UUID for HeaderFilter & EntityFilter
        #      (instead of 'username').
        info[ID_VERSION] = '1.6'
        info.update((e_id, exporter()) for e_id, exporter in self.registry)

        return info

    def get_filename(self) -> str:
        return 'config-{}.json'.format(
            date_format(localtime(now()), 'DATETIME_FORMAT'),
        )

    def get(self, *args, **kwargs):
        # NB: 'indent' is given to have a human-readable file.
        #     'separators' is given to avoid trailing spaces (see json.dumps()'s doc)
        return HttpResponse(
            json_dump(self.get_info(), indent=1, separators=(',', ': ')),
            headers={
                'Content-Type': 'application/json',
                'Content-Disposition': f'attachment; filename="{self.get_filename()}"',
            },
        )


# NB about the xframe: the form uses an-iframe (there is a FileField) & we
#    potentially need to display validation errors.
@method_decorator(xframe_options_sameorigin, name='dispatch')
class ConfigImport(generic.CremeFormPopup):
    form_class = ImportForm
    permissions = STAFF_PERM
    title = _('Import a configuration')
    submit_label = _('Import')
