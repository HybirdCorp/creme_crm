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

from itertools import chain
from collections import defaultdict
from logging import debug

from django.db import models
from django.db.models.query_utils import Q
from django.forms import MultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.models import RelationType, CustomField
from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.gui.listview import get_field_name_from_pattern
from creme_core.utils.meta import get_flds_with_fk_flds_str
from creme_core.utils.id_generator import generate_string_id_and_save


#TODO: create and edit form ????

class HeaderFilterForm(CremeModelForm):
    fields        = MultipleChoiceField(label=_(u'Regular fields'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = MultipleChoiceField(label=_(u'Custom fields'),  required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = MultipleChoiceField(label=_(u'Relations'),      required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = MultipleChoiceField(label=_(u'Functions'),      required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = HeaderFilter
        exclude = ('id', 'is_custom') #TODO: use editable=False in model instead ???

    def __init__(self, *args, **kwargs):
        super(HeaderFilterForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields

        fields['user'].empty_label = ugettext(u'All users')

        ct = ContentType.objects.get_for_id(instance.entity_type_id) if instance.id else \
             self.initial.get('content_type')
        self._entity_type = ct
        model = ct.model_class()

        #caches
        self._relation_types = RelationType.objects.filter(Q(subject_ctypes=ct)|Q(subject_ctypes__isnull=True)).order_by('predicate')
        self._custom_fields  = CustomField.objects.filter(content_type=ct)

        fields_choices = set(chain(get_flds_with_fk_flds_str(model, 1), get_flds_with_fk_flds_str(model, 0)))
        fields_choices = sorted(fields_choices, key=lambda k: ugettext(k[1]))

        fields['fields'].choices = fields_choices
        fields['custom_fields'].choices = [(cf.id, cf.name) for cf in self._custom_fields]
        fields['relations'].choices = [(rtype.id, rtype.predicate) for rtype in self._relation_types]
        fields['functions'].choices = [(f.name, f.verbose_name) for f in model.function_fields]

        if instance.id:
            initial_data = defaultdict(list)

            for hfi in HeaderFilterItem.objects.filter(header_filter__id=instance.id).order_by('order'):
                initial_data[hfi.type].append(hfi)

            fields['fields'].initial = [get_field_name_from_pattern(hfi.filter_string) for hfi in initial_data[HFI_FIELD]]
            fields['custom_fields'].initial = [int(hfi.name) for hfi in initial_data[HFI_CUSTOM]]
            fields['relations'].initial = [hfi.relation_predicat_id for hfi in initial_data[HFI_RELATION]]
            fields['functions'].initial = [hfi.name for hfi in initial_data[HFI_FUNCTION]]

    #NB: _get_cfield_name() & _get_rtype() : we do linear searches because
    #   there are very few searches => build a dict wouldn't be faster
    def _get_cfield(self, cfield_id):
        for cfield in self._custom_fields:
            if cfield.id == cfield_id:
                return cfield

    def _get_rtype(self, rtype_id):
        for rtype in self._relation_types:
            if rtype.id == rtype_id:
                return rtype

    def clean(self):
        cleaned_data = self.cleaned_data
        fields    = cleaned_data['fields']
        cfs       = cleaned_data['custom_fields']
        relations = cleaned_data['relations']
        functions = cleaned_data['functions']

        if not (fields or cfs or relations or functions):
            raise ValidationError(ugettext(u"You have to choose at least one element in available lists."))

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True
        instance.entity_type = ct

        if instance.id:
            for hfi in instance.header_filter_items.all():
                hfi.delete()

            super(HeaderFilterForm, self).save()
        else:
            super(HeaderFilterForm, self).save(commit=False)
            generate_string_id_and_save(HeaderFilter, [instance], 'creme_core-userhf_%s-%s' % (ct.app_label, ct.model))

        model = instance.entity_type.model_class()
        items = []

        build = HeaderFilterItem.build_4_field
        items.extend(build(model=model, name=name) for name in cleaned_data['fields'])

        build = HeaderFilterItem.build_4_customfield
        get_cf = self._get_cfield
        items.extend(build(get_cf(int(cfield_id))) for cfield_id in cleaned_data['custom_fields'])

        build = HeaderFilterItem.build_4_relation
        get_rtype = self._get_rtype
        items.extend(build(get_rtype(rtype_id)) for rtype_id in cleaned_data['relations'])

        get_function_field = model.function_fields.get
        build = HeaderFilterItem.build_4_functionfield
        items.extend(build(get_function_field(name)) for name in cleaned_data['functions'])

        instance.set_items(items)

        return instance
