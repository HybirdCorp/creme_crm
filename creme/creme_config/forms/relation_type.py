################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.forms import BooleanField, CharField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.forms import base as core_forms
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.models import (
    CremePropertyType,
    RelationType,
    SemiFixedRelationType,
)

_CTypesField = partial(
    core_fields.MultiEntityCTypeChoiceField,
    required=False,
    label=_('Type constraint'),
    help_text=_('No constraint means that all types are accepted.'),
)
_PropertyTypesField = partial(
    core_fields.PropertyTypesChoiceField,
    required=False,
    queryset=CremePropertyType.objects.all(),
)


class _RelationTypeForm(core_forms.CremeForm):
    error_messages = {
        'property_types_collision':  _(
            'These property types cannot be mandatory and forbidden at the '
            'same time: %(properties)s'
        ),
    }

    subject_ctypes = _CTypesField()
    subject_properties = _PropertyTypesField(
        label=_('Mandatory properties'),
        help_text=_('The subject must have all the selected properties.'),
    )
    subject_forbidden_properties = _PropertyTypesField(
        label=_('Forbidden properties'),
        help_text=_('The subject cannot have any of the selected properties.'),
    )

    subject_predicate = CharField(label=_('Subject => object'))
    subject_is_copiable = BooleanField(
        label=_('Direct relationship is copiable'), initial=True, required=False,
        help_text=_(
            'Are the relationships with this type copied when the subject entity is cloned?'
        ),
    )
    subject_min_display = BooleanField(
        label=_("Display once on the subject's page"), required=False,
        help_text=_(
            'Do not display in the «Relationships» block (detail-view of '
            'subject) when it is already displayed by another block.'
        ),
    )

    object_predicate = CharField(label=_('Object => subject'))
    object_is_copiable = BooleanField(
        label=_('Symmetrical relationship is copiable'), initial=True, required=False,
        help_text=_(
            'Are the relationships with this type copied when the object entity is cloned?'
        ),
    )
    object_min_display = BooleanField(
        label=_("Display once on the object's page"), required=False,
        help_text=_(
            'Do not display in the «Relationships» block (detail-view of '
            'object) when it is already displayed by another block.'
        ),
    )

    object_ctypes = _CTypesField()
    object_properties = _PropertyTypesField(
        label=_('Mandatory properties'),
        help_text=_('The object must have all the selected properties.'),
    )
    object_forbidden_properties = _PropertyTypesField(
        label=_('Forbidden properties'),
        help_text=_('The object cannot have any of the selected properties.'),
    )

    blocks = core_forms.FieldBlockManager(
        {
            'id': 'subject',
            'label': _('Subject'),
            'fields': [
                'subject_ctypes', 'subject_properties', 'subject_forbidden_properties',
            ],
        }, {
            'id': 'predicate',
            'label': _('Verb/Predicate'),
            'fields': [
                'subject_predicate', 'subject_is_copiable', 'subject_min_display',
                'object_predicate', 'object_is_copiable', 'object_min_display',
            ],
        }, {
            'id': 'object',
            'label': _('Object'),
            'fields': [
                'object_ctypes', 'object_properties', 'object_forbidden_properties',
            ],
        },
    )

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            for field1, field2 in [
                ('subject_properties', 'subject_forbidden_properties'),
                ('object_properties',  'object_forbidden_properties'),
            ]:
                subject_ptypes_collision = {
                    *cdata.get(field1),
                } & {*cdata.get(field2)}
                if subject_ptypes_collision:
                    self.add_error(
                        field2,
                        ValidationError(
                            self.error_messages['property_types_collision'],
                            code='property_types_collision',
                            params={
                                'properties': ', '.join(
                                    str(ptype) for ptype in subject_ptypes_collision
                                ),
                            }
                        ),
                    )

        return cdata

    def save(self,
             pk_subject='creme_config-subject_userrelationtype',
             pk_object='creme_config-object_userrelationtype',
             generate_pk=True,
             *args, **kwargs):
        get_data = self.cleaned_data.get

        subject_ctypes = [ct.model_class() for ct in get_data('subject_ctypes')]
        object_ctypes  = [ct.model_class() for ct in get_data('object_ctypes')]

        return RelationType.objects.smart_update_or_create(
            (
                pk_subject,
                get_data('subject_predicate'),
                subject_ctypes,
                get_data('subject_properties'),
                get_data('subject_forbidden_properties'),
            ),
            (
                pk_object,
                get_data('object_predicate'),
                object_ctypes,
                get_data('object_properties'),
                get_data('object_forbidden_properties'),
            ),
            is_custom=True, generate_pk=generate_pk,
            is_copiable=(
                get_data('subject_is_copiable'), get_data('object_is_copiable')
            ),
            minimal_display=(
                get_data('subject_min_display'), get_data('object_min_display')
            ),
        )


class RelationTypeCreationForm(_RelationTypeForm):
    pass


class RelationTypeEditionForm(_RelationTypeForm):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        sym_instance = instance.symmetric_type
        fields = self.fields

        fields['subject_ctypes'].initial = instance.subject_ctypes.values_list('id', flat=True)
        fields[
            'subject_properties'
        ].initial = instance.subject_properties.values_list('id', flat=True)
        fields[
            'subject_forbidden_properties'
        ].initial = instance.subject_forbidden_properties.values_list('id', flat=True)

        fields['subject_predicate'].initial = instance.predicate
        fields['object_predicate'].initial = sym_instance.predicate

        fields['object_ctypes'].initial = instance.object_ctypes.values_list('id', flat=True)
        fields[
            'object_properties'
        ].initial = instance.object_properties.values_list('id', flat=True)
        fields[
            'object_forbidden_properties'
        ].initial = instance.object_forbidden_properties.values_list('id', flat=True)

        fields['subject_is_copiable'].initial = instance.is_copiable
        fields['object_is_copiable'].initial = sym_instance.is_copiable

        fields['subject_min_display'].initial = instance.minimal_display
        fields['object_min_display'].initial = sym_instance.minimal_display

    def save(self, *args, **kwargs):
        instance = self.instance

        return super().save(
            pk_subject=instance.id,
            pk_object=instance.symmetric_type_id,
            generate_pk=False,
        )


class NotCustomRelationTypeEditionForm(core_forms.CremeForm):
    subject_min_display = BooleanField(
        label=_("…the subject's page"), required=False,
        help_text=_(
            'Do not display in the «Relationships» block (detail-view of '
            'subject) when it is already displayed by another block.'
        ),
    )
    object_min_display = BooleanField(
        label=_("…the object's page"), required=False,
        help_text=_(
            'Do not display in the «Relationships» block (detail-view of '
            'object) when it is already displayed by another block.'
        ),
    )

    blocks = core_forms.FieldBlockManager(
        {
            'id': 'minimal_display',
            # Translators: the end of the sentence is "…the subject's page" or
            # "…the object's page".
            'label': _('Display once on…'),
            'fields': ['subject_min_display', 'object_min_display'],
        },
    )

    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        fields = self.fields
        fields['subject_min_display'].initial = instance.minimal_display
        fields['object_min_display'].initial = instance.symmetric_type.minimal_display

    @atomic
    def save(self, *args, **kwargs) -> RelationType:
        instance: RelationType = self.instance
        get_data = self.cleaned_data.get
        instance.minimal_display = get_data('subject_min_display')
        instance.save()

        sym = instance.symmetric_type
        sym.minimal_display = get_data('object_min_display')
        sym.save()

        return instance


class SemiFixedRelationTypeCreationForm(core_forms.CremeModelForm):
    semi_relation = core_fields.RelationEntityField(
        label=_('Type and object'), autocomplete=True,
        allowed_rtypes=RelationType.objects.filter(is_internal=False),
        credentials=EntityCredentials.VIEW,
    )

    class Meta:
        model = SemiFixedRelationType
        exclude = ('relation_type', 'object_entity')

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            rtype, entity = cdata['semi_relation']

            if SemiFixedRelationType.objects.filter(
                relation_type=rtype, object_entity_id=entity.id,
            ).exists():
                raise ValidationError(
                    _(
                        'A semi-fixed type of relationship with '
                        'this type and this object already exists.'
                    ),
                    code='not_unique',
                )

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance
        instance.relation_type, instance.real_object = self.cleaned_data['semi_relation']

        return super().save(*args, **kwargs)


class SemiFixedRelationTypeEditionForm(core_forms.CremeModelForm):
    class Meta:
        model = SemiFixedRelationType
        fields = ('predicate',)
