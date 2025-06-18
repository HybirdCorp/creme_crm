################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2025  Hybird
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

import logging

from django.contrib.auth import get_user_model
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.job import JobForm

logger = logging.getLogger(__name__)


class CruditySynchronizeJobForm(JobForm):
    user = ModelChoiceField(
        label=_('Default owner user'),
        empty_label=None, queryset=None,
        help_text=_(
            'E.g. user owning emails/folder/documents '
            'created during the emails synchronization.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_f = self.fields['user']
        user_f.queryset = get_user_model().objects.filter(is_staff=False)

        try:
            user_f.initial = self.instance.data['user']
        except Exception:
            logger.exception(
                'Error in CruditySynchronizeJobForm.__init__() with user initialisation.'
            )

    def save(self, *args, **kwargs):
        self.instance.data = {'user': self.cleaned_data['user'].id}

        return super().save(*args, **kwargs)
