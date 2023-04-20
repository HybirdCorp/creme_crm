################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.db.models.query import Q
from django.utils.translation import gettext_lazy as _

from creme import emails
from creme.creme_core import forms as core_forms


class CampaignAddMLForm(core_forms.CremeForm):
    mailing_lists = core_forms.MultiCreatorEntityField(
        label=_('Lists'), required=False, model=emails.get_mailinglist_model(),
    )

    blocks = core_forms.FieldBlockManager({
        'id': 'general', 'label': _('Mailing lists'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = entity
        self.fields['mailing_lists'].q_filter = ~Q(
            id__in=[*entity.mailing_lists.values_list('id', flat=True)],
        )

    def save(self):
        add_ml = self.campaign.mailing_lists.add
        for ml in self.cleaned_data['mailing_lists']:
            add_ml(ml)
