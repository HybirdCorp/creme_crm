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

from __future__ import annotations

from json import dumps as json_dump

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_sameorigin

from creme.creme_core.auth import STAFF_PERM
from creme.creme_core.views import generic

from ..core.exporters import EXPORTERS
from ..forms.transfer import ImportForm


class ConfigExport(generic.CheckedView):
    permissions = STAFF_PERM
    registry = EXPORTERS

    def get_info(self) -> dict:
        return self.registry.export()

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
