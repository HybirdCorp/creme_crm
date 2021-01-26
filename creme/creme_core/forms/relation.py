# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..models import CremeEntity, Relation, RelationType, SemiFixedRelationType
from ..utils import entities_to_str
from . import fields as core_fields
from .base import CremeForm, FieldBlockManager


class _RelationsCreateForm(CremeForm):
    relations = core_fields.MultiRelationEntityField(
        label=_('Relationships'), required=False, autocomplete=True,
    )
    semifixed_rtypes = ModelMultipleChoiceField(
        label=_('Semi-fixed types of relationship'),
        queryset=SemiFixedRelationType.objects.none(),
        required=False,
    )

    error_messages = {
        'duplicates': _('There are duplicates: %(duplicates)s'),
        'link_themselves': _('An entity can not be linked to itself : %(entities)s'),
        'empty': _('You must give one relationship at least.'),
        'missing_property_single': _(
            '«%(subject)s» must have the property «%(property)s» '
            'in order to use the relationship «%(predicate)s»'
        ),
        'missing_property_multi': _(
            '«%(subject)s» must have a property in «%(properties)s» '
            'in order to use the relationship «%(predicate)s»'
        ),
    }

    def __init__(self, subjects, content_type, relations_types=None, *args, **kwargs):
        """Constructor.
        @param subjects: CremeEntity instances that will be the subjects of Relations.
        @param content_type: Type of the subjects.
        @param relations_types: Sequence of RelationTypes ids to narrow to these types ;
               A empty sequence means all types compatible with the parameter 'content_type'.
        """
        super().__init__(*args, **kwargs)
        self.subjects = subjects
        self.subjects_ids = subjects_ids = frozenset(s.id for s in subjects)

        fields = self.fields
        # TODO: improve queries ??
        user = self.user
        entities = [
            sfrt.object_entity
            for sfrt in SemiFixedRelationType.objects
                                             .exclude(object_entity__in=subjects_ids)
                                             .select_related('object_entity')
        ]
        sfrt_queryset = SemiFixedRelationType.objects.filter(
            object_entity__in=filter(user.has_perm_to_link, entities),
        )

        if not relations_types:
            relations_types = RelationType.objects.compatible(content_type)
            sfrt_queryset = sfrt_queryset.filter(
                Q(relation_type__subject_ctypes=content_type)
                | Q(relation_type__subject_ctypes__isnull=True)
            )
        else:
            sfrt_queryset = sfrt_queryset.filter(relation_type__in=relations_types)

        fields['semifixed_rtypes'].queryset = sfrt_queryset

        # TODO: add a qfilter to exclude the subjects from possible objects
        relations_field = fields['relations']
        relations_field.allowed_rtypes = relations_types
        relations_field.initial = [(relations_field.allowed_rtypes.all()[0], None)]

    def _check_duplicates(self, relations, user):
        future_relations = set()
        duplicates = []

        for rtype, entity in relations:
            r_id = f'{rtype.id}#{entity.id}'

            if r_id in future_relations:
                duplicates.append((rtype, entity))
            else:
                future_relations.add(r_id)

        if duplicates:
            raise ValidationError(
                self.error_messages['duplicates'],
                params={
                    'duplicates': ', '.join(
                        f'({rtype}, {e.allowed_str(user)})' for rtype, e in duplicates
                    ),
                },
                code='duplicates',
            )

    # TODO: indicates all subjects which miss properties ?
    # TODO: filter & display these invalid subjects (like non editable subjects)
    def _check_properties(self, rtypes):
        subjects = self.subjects
        need_validation = False
        ptypes_contraints = OrderedDict()

        for rtype in rtypes:
            if rtype.id not in ptypes_contraints:
                properties = dict(rtype.subject_properties.values_list('id', 'text'))
                ptypes_contraints[rtype.id] = (rtype, properties)

                if properties:
                    need_validation = True

        if not need_validation:
            return

        CremeEntity.populate_properties(subjects)

        for subject in subjects:
            for rtype, needed_properties in ptypes_contraints.values():
                if not needed_properties:
                    continue

                subject_prop_ids = {p.type_id for p in subject.get_properties()}

                if any(
                    ptype_id not in subject_prop_ids
                    for ptype_id in needed_properties.keys()
                ):
                    if len(needed_properties) == 1:
                        raise ValidationError(
                            self.error_messages['missing_property_single'],
                            params={
                                'subject':    subject,
                                'property':   next(iter(needed_properties.values())),
                                'predicate':  rtype.predicate,
                            },
                            code='missing_property_single',
                        )
                    else:
                        raise ValidationError(
                            self.error_messages['missing_property_multi'],
                            params={
                                'subject': subject,
                                'properties': '/'.join(
                                    sorted(map(str, needed_properties.values()))
                                ),
                                'predicate': rtype.predicate,
                            },
                            code='missing_property_multi',
                        )

    def _check_loops(self, relations):
        subjects_ids = self.subjects_ids
        bad_objects = [
            str(entity)
            for rtype, entity in relations
            if entity.id in subjects_ids
        ]

        if bad_objects:
            raise ValidationError(
                self.error_messages['link_themselves'],
                params={'entities': ', '.join(bad_objects)},
                code='link_themselves',
            )

    def clean_relations(self):
        relations = self.cleaned_data['relations']

        self._check_duplicates(relations, self.user)
        self._check_loops(relations)
        self._check_properties([rtype for rtype, e_ in relations])

        return relations

    def clean_semifixed_rtypes(self):
        sf_rtypes = self.cleaned_data['semifixed_rtypes']
        self._check_properties([sf_rtype.relation_type for sf_rtype in sf_rtypes])

        return sf_rtypes

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            relations_desc = cdata['relations']
            # TODO: improve queries ??
            relations_desc.extend(
                (sfrt.relation_type, sfrt.object_entity)
                for sfrt in cdata['semifixed_rtypes']
            )

            if not relations_desc:
                raise ValidationError(self.error_messages['empty'], code='empty')

            self._check_duplicates(relations_desc, self.user)

            self.relations_desc = relations_desc

        return cdata

    def save(self):
        user = self.user

        Relation.objects.safe_multi_save(
            Relation(
                user=user,
                subject_entity=subject,
                type=rtype,
                object_entity=object_entity,
            )
            for subject in self.subjects
            for rtype, object_entity in self.relations_desc
        )


class RelationCreateForm(_RelationsCreateForm):
    def __init__(self, subject, relations_types=None, *args, **kwargs):
        super().__init__(
            [subject], subject.entity_type,
            relations_types=relations_types,
            *args, **kwargs
        )


class MultiEntitiesRelationCreateForm(_RelationsCreateForm):
    entities_lbl = core_fields.ReadonlyMessageField(label=_('Related entities'))

    # TODO: use Meta.fields ?? (beware to bad_entities_lbl)
    blocks = FieldBlockManager({
        'id': 'general',
        'label': _('General information'),
        'fields': ['entities_lbl', 'relations', 'semifixed_rtypes'],
    })

    def __init__(self, subjects, forbidden_subjects, relations_types=None, *args, **kwargs):
        first_subject = subjects[0] if subjects else forbidden_subjects[0]
        super().__init__(
            subjects, first_subject.entity_type,
            relations_types=relations_types,
            *args, **kwargs
        )

        user = self.user
        fields = self.fields
        fields['entities_lbl'].initial = entities_to_str(
            subjects, user,
        ) if subjects else gettext('NONE !')

        if forbidden_subjects:
            fields['bad_entities_lbl'] = core_fields.ReadonlyMessageField(
                label=gettext('Unlinkable entities'),
                initial=entities_to_str(forbidden_subjects, user),
            )
