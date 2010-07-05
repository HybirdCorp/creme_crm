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

from django.forms.widgets import HiddenInput
from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeEntityForm
from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import DateTimeWidget

from persons.models import Contact

from projects.models import Project


class ProjectEditForm(CremeEntityForm):
    start_date          = DateTimeField(label=_(u'Début du projet'), required=True, widget=DateTimeWidget())
    end_date            = DateTimeField(label=_(u'Fin du projet'), required=True, widget=DateTimeWidget())
    effective_end_date  = DateTimeField(widget=HiddenInput(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Project


class ProjectCreateForm(ProjectEditForm):
    responsible = MultiCremeEntityField(label=_(u'Responsable(s) du projet'),
                                        required=True, model=Contact)

    def save(self):
        super(ProjectCreateForm, self).save()
        self.instance.add_responsibles(self.cleaned_data['responsible'])
