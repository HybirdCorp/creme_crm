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
    entity_type   = ModelChoiceField(queryset=ContentType.objects.none(), widget=HiddenInput()) #TODO: store in a attribute instead....
    fields        = MultipleChoiceField(label=_(u'Champs normaux'),       required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    custom_fields = MultipleChoiceField(label=_(u'Champs personnalisés'), required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    relations     = MultipleChoiceField(label=_(u'Relations'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)
    functions     = MultipleChoiceField(label=_(u'Fonctions'),            required=False, choices=(), widget=OrderedMultipleChoiceWidget)

    class Meta:
        model = HeaderFilter
        exclude = ('id', 'is_custom')

    def __init__(self, *args, **kwargs):
        super(HeaderFilterForm, self).__init__(*args, **kwargs)
        initial  = self.initial
        instance = self.instance
        fields   = self.fields

        if instance.id:
            ct_id = instance.entity_type.id
        else:
            ct_id = initial.get('content_type_id')

        fields['entity_type'].initial = ct_id
        fields['entity_type'].queryset = ContentType.objects.filter(pk=ct_id)
        ct = ContentType.objects.get_for_id(ct_id) if not instance.id else instance.entity_type
        model_klass = ct.model_class()

        fields['fields'].choices = get_flds_with_fk_flds_str(model_klass, 1)
        fields['custom_fields'].choices = CustomField.objects.filter(content_type=ct).values_list('id', 'name')
        fields['relations'].choices = RelationType.objects.filter(Q(subject_ctypes=ct)|Q(subject_ctypes__isnull=True)).order_by('predicate').values_list('id', 'predicate')
        fields['functions'].choices = ((f['name'], f['verbose_name']) for f in model_klass.users_allowed_func)

        if instance.id:
            #TODO: do 1 query instead of 3
            HFI_filter = HeaderFilterItem.objects.filter(header_filter__id=instance.id).order_by('order').filter

            fields['fields'].initial    = [fs.rpartition('__')[0] for fs in HFI_filter(type=HFI_FIELD).values_list('filter_string', flat=True)]
            fields['custom_fields'].initial = [int(i) for i in HFI_filter(type=HFI_CUSTOM).values_list('name', flat=True)]
            fields['relations'].initial = HFI_filter(type=HFI_RELATION).values_list('relation_predicat_id', flat=True)
            fields['functions'].initial = HFI_filter(type=HFI_FUNCTION).values_list('name', flat=True)

    def save(self):
        cleaned_data = self.cleaned_data
        instance = self.instance
        ct = cleaned_data['entity_type']

        instance.is_custom = True
        instance.entity_type = ct

        if instance.id:
            for hfi in HeaderFilterItem.objects.filter(header_filter__id=instance.id): #TODO: use related_name ??
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

        get_cfield = CustomField.objects.get
        for cfield in cleaned_data['custom_fields']:
            items_2_save.append(HeaderFilterItem(name=cfield,
                                                 title=get_cfield(pk=cfield).name,
                                                 type=HFI_CUSTOM,
                                                 has_a_filter=False, #TODO
                                                 editable=False, #TODO: make it editable
                                                 sortable=False, #TODO: make it sortable
                                                 filter_string=pattern % field))

        #TODO: regroup the retrieving with a filter + in_bulks ??  ==> No use a 'cache' instead
        get_relationtype = RelationType.objects.get
        for rel in cleaned_data['relations']:
            rel_name = get_relationtype(pk=rel).predicate #TODO 18n

            items_2_save.append(HeaderFilterItem(name=rel_name.replace(' ', '_').replace("'", "_"),
                                                 title=rel_name,#.replace("'", " "),
                                                 type=HFI_RELATION,
                                                 has_a_filter=False,
                                                 editable=False ,
                                                 filter_string="",
                                                 relation_predicat_id=rel))

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
