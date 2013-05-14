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

from django.forms import CharField, ModelMultipleChoiceField
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremePropertyType, RelationType, SemiFixedRelationType
from creme.creme_core.forms import CremeForm, CremeModelForm, FieldBlockManager
from creme.creme_core.forms.fields import RelationEntityField
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.utils import Q_creme_entity_content_types


_entities_ct = Q_creme_entity_content_types()
_ct_helptext = _(u'No constraint means that all types are accepted')
_ct_label    = _(u'Type constraint')

_all_props   = CremePropertyType.objects.all()
_prop_label  = _(u'Properties constraint')


class _RelationTypeBaseForm(CremeForm):
    subject_ctypes     = ModelMultipleChoiceField(label=_ct_label, queryset=_entities_ct, help_text=_ct_helptext,
                                                  widget=UnorderedMultipleChoiceWidget, required=False)
    subject_properties = ModelMultipleChoiceField(label=_prop_label, queryset=_all_props,
                                                  widget=UnorderedMultipleChoiceWidget, required=False)

    #TODO: language....
    subject_predicate  = CharField(label=_(u'Subject => object'))
    object_predicate   = CharField(label=_(u'Object => subject'))

    object_ctypes      = ModelMultipleChoiceField(label=_ct_label, queryset=_entities_ct, help_text=_ct_helptext,
                                                  widget=UnorderedMultipleChoiceWidget, required=False)
    object_properties  = ModelMultipleChoiceField(label=_prop_label, queryset=_all_props,
                                                  widget=UnorderedMultipleChoiceWidget, required=False)

    blocks = FieldBlockManager(('subject',   _(u'Subject'),        ('subject_ctypes', 'subject_properties')),
                               ('predicate', _(u'Verb/Predicate'), ('subject_predicate', 'object_predicate')),
                               ('object',    _(u'Object'),         ('object_ctypes', 'object_properties')),
                              )


class RelationTypeCreateForm(_RelationTypeBaseForm):
    def save(self):
        get_data = self.cleaned_data.get

        subject_ctypes = [ct.model_class() for ct in get_data('subject_ctypes')]
        object_ctypes  = [ct.model_class() for ct in get_data('object_ctypes')]

        RelationType.create(('creme_config-subject_userrelationtype', get_data('subject_predicate'), subject_ctypes, get_data('subject_properties')),
                            ('creme_config-object_userrelationtype',  get_data('object_predicate'),  object_ctypes,  get_data('object_properties')),
                            is_custom=True, generate_pk=True,
                           )


class RelationTypeEditForm(_RelationTypeBaseForm):
    def __init__(self, instance, *args, **kwargs):
        super(RelationTypeEditForm, self).__init__(*args, **kwargs)

        self.instance = instance
        fields = self.fields

        #TODO: use values_list() ???
        fields['subject_ctypes'].initial     = [ct.id for ct in instance.subject_ctypes.all()]
        fields['subject_properties'].initial = [pt.id for pt in instance.subject_properties.all()]

        fields['subject_predicate'].initial = instance.predicate
        fields['object_predicate'].initial  = instance.symmetric_type.predicate

        fields['object_ctypes'].initial     = [ct.id for ct in instance.object_ctypes.all()]
        fields['object_properties'].initial = [pt.id for pt in instance.object_properties.all()]

    def save(self): #factorise with RelationTypeCreateForm.save()
        instance = self.instance

        get_data = self.cleaned_data.get

        subject_ctypes = [ct.model_class() for ct in get_data('subject_ctypes')]
        object_ctypes  = [ct.model_class() for ct in get_data('object_ctypes')]

        RelationType.create((instance.id,                get_data('subject_predicate'), subject_ctypes, get_data('subject_properties')),
                            (instance.symmetric_type_id, get_data('object_predicate'),  object_ctypes,  get_data('object_properties')),
                            is_custom=True,
                           )


class SemiFixedRelationTypeCreateForm(CremeModelForm):
    semi_relation = RelationEntityField(label=_('Type and object'),
                                        allowed_rtypes=RelationType.objects.filter(is_internal=False),
                                       )

    class Meta:
        model = SemiFixedRelationType
        exclude = ('relation_type', 'object_entity')

    #def __init__(self, *args, **kwargs):
        #super(SemiFixedRelationTypeCreateForm, self).__init__(*args, **kwargs)
        #TODO: improve RelationEntityField in order to put this queryset in the declaration
        #      for now the queryset is immediately executed, so RelationTypes create after are not used.
        #self.fields['semi_relation'].allowed_rtypes = RelationType.objects.filter(is_internal=False) \
        #                                                                  .values_list('id', flat=True)

    def clean(self):
        cdata = super(SemiFixedRelationTypeCreateForm, self).clean()

        if not self._errors:
            rtype, entity = cdata['semi_relation']

            if SemiFixedRelationType.objects.filter(relation_type=rtype, object_entity=entity).exists():
                raise ValidationError(_(u"A semi-fixed type of relationship with this type and this object already exists."))

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.relation_type, instance.object_entity = self.cleaned_data['semi_relation']

        return super(SemiFixedRelationTypeCreateForm, self).save(*args, **kwargs)
