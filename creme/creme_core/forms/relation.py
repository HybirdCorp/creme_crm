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

from django.forms.util import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, Relation, RelationType
from creme_core.forms import CremeForm
from creme_core.forms.fields import RelatedEntitiesField
from creme_core.forms.widgets import RelationListWidget


class RelationCreateForm(CremeForm):
    relations = RelatedEntitiesField(label=_(u'Relations'),
                                     widget=RelationListWidget(),
                                     required=True,
                                     use_ctype=True)

    def __init__(self, subject, user_id, *args, **kwargs):
        super(RelationCreateForm, self).__init__(*args, **kwargs)
        self.subject = subject
        self.user_id = user_id

        if subject:
            self.fields['relations'].widget.subject = subject.id

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        # check existence of all selected predicates and entities
        relations = set(cleaned_data.get('relations', []))

        if not relations:
            raise ValidationError(_(u'Aucune relation'))

        predicate_ids    = set(entry[0] for entry in relations)
        content_type_ids = set(entry[1] for entry in relations)
        entity_ids       = set(entry[2] for entry in relations)

        if RelationType.objects.filter(pk__in=predicate_ids).count() < len(predicate_ids):
            raise ValidationError(_(u"Certains prédicats n'existent pas"))

        if ContentType.objects.filter(pk__in=content_type_ids).count() < len(content_type_ids):
            raise ValidationError(_(u"Certains types d'entité n'existent pas"))

        if CremeEntity.objects.filter(pk__in=entity_ids).count() < len(entity_ids):
            raise ValidationError(_(u"Certaines entités n'existent pas"))

        cleaned_data['relations'] = relations

        # TODO : add validation for relations (check doubles, and existence)
        return cleaned_data

    def save(self):
        #ctype useless (after a refactoring) ??? (maybe useful for credentials)
        for predicate_id, ctype, entity_id in self.cleaned_data.get('relations', ()):
            relation = Relation()
            relation.user_id = self.user_id
            relation.type_id = predicate_id

            #relation.subject_id = self.subject.id
            #relation.subject_content_type_id = self.subject.entity_type_id
            relation.subject_entity = self.subject

            #relation.object_id = entity_id
            #relation.object_content_type_id = ctype
            relation.object_entity_id = entity_id
            relation.save()
