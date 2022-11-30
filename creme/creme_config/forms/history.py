################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import HistoryConfigItem, RelationType


class HistoryConfigForm(CremeForm):
    relation_types = ModelMultipleChoiceField(
        label=_('Relation types'),
        queryset=RelationType.objects.filter(historyconfigitem=None, enabled=True),
        help_text=_(
            'If an entity is linked to other entities by a Relationship of '
            'this type, the history lines that are about the edition of this '
            'entity will appear in the history of the others entities.'
        ),
        widget=UnorderedMultipleChoiceWidget(columntype='wide'),
    )

    def save(self, *args, **kwargs):
        create_hci = HistoryConfigItem.objects.create

        for rtype in self.cleaned_data['relation_types']:
            create_hci(relation_type=rtype)
