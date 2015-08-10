# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.forms.widgets import DateTimeWidget

from ..models import RecurrentGenerator


class RecurrentGeneratorEditForm(CremeEntityForm):
    first_generation = DateTimeField(label=_(u'Date of the first generation'),
                                     widget=DateTimeWidget(),
                                    )

    class Meta(CremeEntityForm.Meta):
        model = RecurrentGenerator

    def __init__(self, *args, **kwargs):
        super(RecurrentGeneratorEditForm, self).__init__(*args, **kwargs)
        if self.instance.last_generation:
            del self.fields['first_generation']


class RecurrentGeneratorCreateForm(RecurrentGeneratorEditForm):
    ct = EntityCTypeChoiceField(label=_(u'Type of resource used as template'))

    def __init__(self, *args, **kwargs):
        from ..registry import recurrent_registry

        #kwargs['user'] = kwargs['initial']['user']
        #super(RecurrentGeneratorCreateForm, self).__init__(data=args[0], **kwargs)
        super(RecurrentGeneratorCreateForm, self).__init__(*args, **kwargs)

        has_perm = self.user.has_perm_to_create
        self.fields['ct'].ctypes = [ctype for ctype in recurrent_registry.ctypes
                                            if has_perm(ctype.model_class())
                                   ]

    def save(self, *args, **kwargs):
        instance = self.instance
        #instance.last_generation = instance.first_generation #todo: in model.save() ??
        instance.ct = self.cleaned_data['ct']

        return super(RecurrentGeneratorCreateForm, self).save(*args, **kwargs)
