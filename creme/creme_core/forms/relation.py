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

from django.db.models import Q
from django.forms import CharField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType
from creme_core.forms.base import CremeEntityForm, FieldBlockManager

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.forms import CremeForm
from creme_core.forms.fields import MultiRelationEntityField
from creme_core.forms.widgets import Label
from creme_core.forms.validators import validate_linkable_entities
from creme_core.utils import entities2unicode


class RelationCreateForm(CremeForm):
    relations = MultiRelationEntityField(label=_(u'Relations'))

    def __init__(self, subject, relations_types=None, *args, **kwargs):
        """
        @param relations_types Sequence of RelationTypes ids to narrow to these types ; or None that means all types compatible with the subject.
        """
        super(RelationCreateForm, self).__init__(*args, **kwargs)
        self.subject = subject

        if not relations_types:
            relations_types = RelationType.get_compatible_ones(subject.entity_type).order_by('predicate').values_list('id', flat=True)

        self.fields['relations'].allowed_rtypes = relations_types

    def _check_duplicates(self, relations, user):
        future_relations = set()
        duplicates = []

        for rtype, entity in relations:
            r_id = '%s#%s' % (rtype.id, entity.id)

            if r_id in future_relations:
                duplicates.append((rtype, entity))
            else:
                future_relations.add(r_id)

        if duplicates:
            raise ValidationError(ugettext(u'There are duplicates: %s') % \
                                      u', '.join(u'(%s, %s)' % (rtype, e.allowed_unicode(user))
                                                     for rtype, e in duplicates
                                                )
                                 )

    def clean_relations(self):
        relations = self.cleaned_data['relations']
        user = self.user

        self._check_duplicates(relations, user)
        validate_linkable_entities([entity for rt_id, entity in relations], user)

        return relations

    @staticmethod
    def _hash_relation(subject_id, rtype_id, object_id):
        return '%s#%s#%s' % (subject_id, rtype_id, object_id)

    def _create_relations(self, subjects):
        user = self.user
        hash_relation = self._hash_relation
        relations_cdata = self.cleaned_data['relations']
        existing_relations_query = Q()

        for subject in subjects:
            for rtype, object_entity in relations_cdata:
                existing_relations_query |= Q(type=rtype, subject_entity=subject.id, object_entity=object_entity.id)

        existing_relations = frozenset(hash_relation(r.subject_entity_id, r.type_id, r.object_entity_id)
                                            for r in Relation.objects.filter(existing_relations_query)
                                      )

        create_relation    = Relation.objects.create

        for subject in subjects:
            for rtype, object_entity in relations_cdata:
                if not hash_relation(subject.id, rtype.id, object_entity.id) in existing_relations:
                    create_relation(user=user,
                                    subject_entity=subject,
                                    type=rtype,
                                    object_entity=object_entity,
                                   )

    def save(self):
        self._create_relations([self.subject])


class MultiEntitiesRelationCreateForm(RelationCreateForm):
    entities_lbl = CharField(label=_(u"Related entities"), widget=Label())
    blocks = FieldBlockManager(('general', _(u'General information'), ['entities_lbl', 'relations']),)

    def __init__(self, subjects, forbidden_subjects, user, relations_types=None, *args, **kwargs):
        subject = subjects[0] if subjects else forbidden_subjects[0]
        super(MultiEntitiesRelationCreateForm, self).__init__(subject=subject, user=user, relations_types=relations_types, *args, **kwargs)
        self.subjects = subjects
        self.user = user
        self.fields['entities_lbl'].initial = entities2unicode(subjects, user) if subjects else ugettext(u'NONE !')

        if forbidden_subjects:
            self.fields['bad_entities_lbl'] = CharField(label=ugettext(u"Unlinkable entities"),
                                                        widget=Label,
                                                        initial=entities2unicode(forbidden_subjects, user)
                                                       )

    def save(self):
        self._create_relations(self.subjects)
