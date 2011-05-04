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
from django.core.exceptions import ValidationError
from django.forms.fields import CharField, ChoiceField
from django.utils.translation import ugettext, ugettext_lazy as _
from creme_core.forms.base import CremeForm
from creme_core.forms.widgets import Label
from creme_core.utils import entities2unicode
from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.gui.bulk_update import bulk_update_registry

class EntitiesBulkUpdateForm(CremeForm):
    entities_lbl = CharField(label=_(u"Entities to update"), widget=Label)
    field_name   = ChoiceField(label=_(u"Field to update"))
    field_value  = CharField(label=_(u"Value"), required=False)

    def __init__(self, model, subjects, forbidden_subjects, user, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).__init__(user, *args, **kwargs)
        self.subjects = subjects
        self.user = user
        self.model = model
        fields = self.fields

        fields['entities_lbl'].initial = entities2unicode(subjects, user) if subjects else ugettext(u'NONE !')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = CharField(label=ugettext(u"Unchangeable entities"),
                                                        widget=Label,
                                                        initial=entities2unicode(forbidden_subjects, user)
                                                       )

        excluded_fields = bulk_update_registry.get_excluded_fields(model)
        #TODO: Add customs fields
        fields['field_name'].choices = sorted(get_flds_with_fk_flds_str(model, deep=0, exclude_func=lambda f: f.name in excluded_fields), key=lambda k: ugettext(k[1]))

    def clean(self, *args, **kwargs):
        super(EntitiesBulkUpdateForm, self).clean(*args, **kwargs)
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data
        
        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']

        field = self.model._meta.get_field(field_name)

        if field_value is None and not field.null:
            raise ValidationError(ugettext(u'This field is required.'))

        if not (field_value or field.blank):
            raise ValidationError(ugettext(u'This field is required.'))

        return cleaned_data

    
    def save(self):
        cleaned_data = self.cleaned_data

        field_value = cleaned_data['field_value']
        field_name  = cleaned_data['field_name']
        self.model.objects.filter(pk__in=self.subjects).update(**{field_name:field_value})