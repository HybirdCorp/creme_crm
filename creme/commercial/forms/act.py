# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms import CremeEntityForm, CremeModelForm, CremeDateTimeField
from creme_core.utils import Q_creme_entity_content_types

from commercial.models import Act, ActObjective


class ActForm(CremeEntityForm):
    start    = CremeDateTimeField(label=_(u"Start"))
    due_date = CremeDateTimeField(label=_(u"Due date"))

    class Meta(CremeEntityForm.Meta):
        model = Act


class ObjectiveForm(CremeModelForm):
    class Meta:
        model = ActObjective
        fields = ('name', 'counter_goal')

    def __init__(self, entity, *args, **kwargs):
        super(ObjectiveForm, self).__init__(*args, **kwargs)
        self.act = entity

        self.fields['counter_goal'].help_text = ugettext(u'Integer value the counter has to reach')

    def save(self, *args, **kwargs):
        self.instance.act = self.act
        super(ObjectiveForm, self).save(*args, **kwargs)


class RelationObjectiveForm(ObjectiveForm):
    class Meta(ObjectiveForm.Meta):
        fields = ObjectiveForm.Meta.fields + ('ctype',)

    def __init__(self, *args, **kwargs):
        super(RelationObjectiveForm, self).__init__(*args, **kwargs)

        ctype_field = self.fields['ctype']
        ctype_field.queryset = Q_creme_entity_content_types()
        ctype_field.empty_label = None
