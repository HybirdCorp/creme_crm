# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import HistoryConfigItem, RelationType
from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget


_HELP_TEXT = _(u"""If an entity is linked to other entities by a relationship of this type,
 the history lines that are about the edition of this entity will appear in the history of the others entities.""")

class HistoryConfigForm(CremeForm):
    relation_types = ModelMultipleChoiceField(label=_(u'Relation types'),
                                              queryset=RelationType.objects.all(),
                                              help_text=_HELP_TEXT,
                                              widget=UnorderedMultipleChoiceWidget(columntype='wide'),
                                             )

    def __init__(self, *args, **kwargs):
        super(HistoryConfigForm, self).__init__(*args, **kwargs)

        self.fields['relation_types'].queryset = \
            RelationType.objects.exclude(pk__in=HistoryConfigItem.objects.values_list('relation_type', flat=True))

    def save(self, *args, **kwargs):
        create_hci = HistoryConfigItem.objects.create

        for rtype in self.cleaned_data['relation_types']:
            create_hci(relation_type=rtype)
