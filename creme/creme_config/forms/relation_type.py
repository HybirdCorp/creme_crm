# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from functools import partial

from django.forms import CharField, ModelMultipleChoiceField, BooleanField
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremePropertyType, RelationType, SemiFixedRelationType
from creme.creme_core.forms import (CremeForm, CremeModelForm,
        FieldBlockManager, RelationEntityField, MultiEntityCTypeChoiceField)
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget


_CTypesField = partial(MultiEntityCTypeChoiceField, required=False,
                       label=_(u'Type constraint'),
                       help_text=_(u'No constraint means that all types are accepted'),
                      )
_PropertyTypesField = partial(ModelMultipleChoiceField, required=False,
                              label=_(u'Properties constraint'),
                              queryset=CremePropertyType.objects.all(),
                              widget=UnorderedMultipleChoiceWidget,
                             )


class RelationTypeCreateForm(CremeForm):
    subject_ctypes     = _CTypesField()
    subject_properties = _PropertyTypesField()

    #TODO: language....
    subject_predicate  = CharField(label=_(u'Subject => object'))
    subject_is_copiable= BooleanField(label=_(u"Direct relationship is copiable"), initial=True, required=False,
                                      help_text=_(u'Are the relationships with this type copied when the subject entity is cloned?')
                                     )
    object_predicate   = CharField(label=_(u'Object => subject'))
    object_is_copiable = BooleanField(label=_(u"Symmetrical relationship is copiable"), initial=True, required=False,
                                      help_text=_(u'Are the relationships with this type copied when the object entity is cloned?')
                                     )

    object_ctypes      = _CTypesField()
    object_properties  = _PropertyTypesField()

    blocks = FieldBlockManager(('subject',   _(u'Subject'),        ('subject_ctypes', 'subject_properties')),
                               ('predicate', _(u'Verb/Predicate'), ('subject_predicate', 'subject_is_copiable',
                                                                    'object_predicate', 'object_is_copiable')),
                               ('object',    _(u'Object'),         ('object_ctypes', 'object_properties')),
                              )

    def save(self, pk_subject='creme_config-subject_userrelationtype',
              pk_object='creme_config-object_userrelationtype',
              generate_pk=True, *args, **kwargs
             ):
        get_data = self.cleaned_data.get

        subject_ctypes = [ct.model_class() for ct in get_data('subject_ctypes')]
        object_ctypes  = [ct.model_class() for ct in get_data('object_ctypes')]

        return RelationType.create((pk_subject, get_data('subject_predicate'), subject_ctypes, get_data('subject_properties')),
                                   (pk_object,  get_data('object_predicate'),  object_ctypes,  get_data('object_properties')),
                                   is_custom=True, generate_pk=generate_pk, is_copiable=(get_data('subject_is_copiable'), get_data('object_is_copiable')),
                                  )


class RelationTypeEditForm(RelationTypeCreateForm):
    def __init__(self, instance, *args, **kwargs):
        super(RelationTypeEditForm, self).__init__(*args, **kwargs)
        self.instance = instance
        fields = self.fields

        fields['subject_ctypes'].initial     = instance.subject_ctypes.values_list('id', flat=True)
        fields['subject_properties'].initial = instance.subject_properties.values_list('id', flat=True)

        fields['subject_predicate'].initial = instance.predicate
        fields['object_predicate'].initial  = instance.symmetric_type.predicate

        fields['object_ctypes'].initial     = instance.object_ctypes.values_list('id', flat=True)
        fields['object_properties'].initial = instance.object_properties.values_list('id', flat=True)

        fields['subject_is_copiable'].initial = instance.is_copiable
        fields['object_is_copiable'].initial = instance.symmetric_type.is_copiable

    def save(self,  *args, **kwargs):
        instance = self.instance

        return super(RelationTypeEditForm, self).save(pk_subject=instance.id, 
                                                      pk_object=instance.symmetric_type_id,
                                                      generate_pk=False,
                                                     )


class SemiFixedRelationTypeCreateForm(CremeModelForm):
    semi_relation = RelationEntityField(label=_('Type and object'),
                                        allowed_rtypes=RelationType.objects.filter(is_internal=False),
                                       )

    class Meta:
        model = SemiFixedRelationType
        exclude = ('relation_type', 'object_entity')

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
