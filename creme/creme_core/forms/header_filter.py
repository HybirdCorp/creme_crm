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

from collections import defaultdict
from logging import debug

from django.db import models
from django.db.models.query_utils import Q
from django.db.models.fields import FieldDoesNotExist
from django.forms import MultipleChoiceField, ModelChoiceField
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM
from creme_core.models import RelationType, RelationPredicate_i18n, CustomField
from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.utils.meta import get_flds_with_fk_flds_str, get_model_field_infos
from creme_core.utils.id_generator import generate_string_id_and_save


#TODO: create and edit form ????

class HeaderFilterForm(CremeModelForm):
    fields        = MultipleChoiceField(label=_(u'Champs normaux'),       required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = MultipleChoiceField(label=_(u'Champs personnalisés'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = MultipleChoiceField(label=_(u'Relations'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = MultipleChoiceField(label=_(u'Fonctions'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = HeaderFilter
        exclude = ('id', 'is_custom')

    def __init__(self, *args, **kwargs):
        super(HeaderFilterForm, self).__init__(*args, **kwargs)
        instance = self.instance
        fields   = self.fields

        if instance.id:
            ct = ContentType.objects.get_for_id(instance.entity_type_id)
        else:
            ct = self.initial.get('content_type')

        self._entity_type = ct
        model = ct.model_class()

        #caches
        self._relation_types = RelationType.objects.filter(Q(subject_ctypes=ct)|Q(subject_ctypes__isnull=True)).order_by('predicate').values_list('id', 'predicate')
        self._custom_fields  = CustomField.objects.filter(content_type=ct)

        fields['fields'].choices = get_flds_with_fk_flds_str(model, 1)
        fields['custom_fields'].choices = [(cf.id, cf.name) for cf in self._custom_fields]
        fields['relations'].choices = self._relation_types
        fields['functions'].choices = ((f['name'], f['verbose_name']) for f in model.users_allowed_func)

        if instance.id:
            initial_data = defaultdict(list)

            for hfi in HeaderFilterItem.objects.filter(header_filter__id=instance.id).order_by('order'):
                initial_data[hfi.type].append(hfi)

            fields['fields'].initial = [hfi.filter_string.rpartition('__')[0] for hfi in initial_data[HFI_FIELD]]
            fields['custom_fields'].initial = [int(hfi.name) for hfi in initial_data[HFI_CUSTOM]]
            fields['relations'].initial = [hfi.relation_predicat_id for hfi in initial_data[HFI_RELATION]]
            fields['functions'].initial = [hfi.name for hfi in initial_data[HFI_FUNCTION]]

    #NB: _get_cfield_name() & _get_predicate() : we do linear searches because
    #   there are very few searches => build a dict wouldn't be faster
    def _get_cfield(self, cfield_id):
        for cfield in self._custom_fields:
            if cfield.id == cfield_id:
                return cfield

    def _get_predicate(self, relation_type_id):
        for id_, predicate in self._relation_types:
            if id_ == relation_type_id:
                return predicate

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

        model_klass  = instance.entity_type.model_class()
        items_2_save = []

        get_metafield = model_klass._meta.get_field
        for field in cleaned_data['fields']:
            try:
                field_infos = get_model_field_infos(model_klass, field)
                field_obj   = field_infos[0]['field']

                pattern = "%s__icontains"
                if isinstance(field_obj, (models.DateField, models.DateTimeField)):
                    pattern = "%s__range"
                elif isinstance(field_obj, models.BooleanField):
                    pattern = "%s__creme-boolean"

                items_2_save.append(HeaderFilterItem(name=field.partition('__')[0],
                                                     title=u" - ".join(unicode(field_info['field'].verbose_name) for field_info in field_infos),
                                                     type=HFI_FIELD,
                                                     has_a_filter=True,
                                                     editable=True,
                                                     sortable=True,
                                                     filter_string=pattern % field))
            except (FieldDoesNotExist, AttributeError), e:
                debug('Exception in HeaderFilterForm.save(): %s', e)

        for cfield_id in cleaned_data['custom_fields']:
            cfield = self._get_cfield(int(cfield_id))

            if cfield.field_type == CustomField.DATE:
                pattern = "%s__value__range"
            elif cfield.field_type == CustomField.BOOL:
                pattern = "%s__value__creme-boolean"
            elif cfield.field_type == CustomField.ENUM:
                pattern = "%s__value__exact"
            else:
                pattern = "%s__value__icontains"

            items_2_save.append(HeaderFilterItem(name=cfield_id,
                                                 title=cfield.name,
                                                 type=HFI_CUSTOM,
                                                 has_a_filter=True,
                                                 editable=False, #TODO: make it editable
                                                 sortable=False, #TODO: make it sortable
                                                 filter_string=pattern % cfield.get_value_class().get_related_name()))

        for relation_type_id in cleaned_data['relations']:
            predicate = self._get_predicate(relation_type_id)

            items_2_save.append(HeaderFilterItem(name=predicate.replace(' ', '_').replace("'", "_"),
                                                 title=predicate,#.replace("'", " "),
                                                 type=HFI_RELATION,
                                                 has_a_filter=False,
                                                 editable=False ,
                                                 filter_string="",
                                                 relation_predicat_id=relation_type_id))

        get_funcname = model_klass.get_users_func_verbose_name
        for func in cleaned_data['functions']:
            items_2_save.append(HeaderFilterItem(name=func,
                                                 title=get_funcname(func),
                                                 type=HFI_FUNCTION,
                                                 has_a_filter=False,
                                                 editable=False,
                                                 filter_string=""))

        for i, hfi in enumerate(items_2_save):
            hfi.order = i + 1
            hfi.header_filter = instance

        generate_string_id_and_save(HeaderFilterItem, items_2_save,
                                    'creme_core-userhfi_%s-%s' % (ct.app_label, ct.model))
