# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.forms import ModelChoiceField, ValidationError  # DateTimeField
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext

from creme.creme_core.forms import CremeEntityForm, CremeForm, MultiRelationEntityField
from creme.creme_core.models import Relation
from creme.creme_core.utils import find_first

from creme.persons import get_organisation_model
from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES

from creme.opportunities.forms.opportunity import OpportunityCreateForm

from .. import get_event_model
from .. import constants


class EventForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = get_event_model()

    def clean(self):
        # cdata = super(CremeEntityForm, self).clean()
        cdata = super().clean()

        if not self._errors:
            end = cdata.get('end_date')

            if end and cdata['start_date'] > end:
                self.add_error('end_date', ugettext(u'The end date must be after the start date.'))

        return cdata


_SYMMETRICS = {
        constants.REL_OBJ_CAME_EVENT:     constants.REL_OBJ_NOT_CAME_EVENT,
        constants.REL_OBJ_NOT_CAME_EVENT: constants.REL_OBJ_CAME_EVENT,
    }

_TYPES = [constants.REL_OBJ_IS_INVITED_TO, constants.REL_OBJ_CAME_EVENT, constants.REL_OBJ_NOT_CAME_EVENT]


class AddContactsToEventForm(CremeForm):
    related_contacts = MultiRelationEntityField(allowed_rtypes=_TYPES, label=_(u'Related contacts'))

    error_messages = {
        'duplicates': _(u'Contact %(contact)s is present twice.'),
    }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('instance')
        # super(AddContactsToEventForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

        # TODO: factorise (_RelationsCreateForm in creme_core) ??
        relations_field = self.fields['related_contacts']
        relations_field.initial = [(relations_field.allowed_rtypes.all()[0], None)]

    def clean_related_contacts(self):
        # Because of the optimisations, the save() algo will be wrong with a contact that is present twice.
        related_contacts = self.cleaned_data['related_contacts']
        contacts_set = set()

        for relationtype, contact in related_contacts:
            if contact.id in contacts_set:
                raise ValidationError(self.error_messages['duplicates'],
                                      params={'contact': contact},
                                      code='duplicates',
                                     )

            contacts_set.add(contact.id)

        return related_contacts

    def save(self):
        # BEWARE: chosen contacts can have already relations with the event ;
        #         we avoid several 'REL_OBJ_IS_INVITED_TO' relations,
        #         'REL_OBJ_CAME_EVENT' override existing 'REL_OBJ_NOT_CAME_EVENT' relations etc...
        event = self.event
        user  = self.user
        relations = Relation.objects
        create_relation = relations.create

        related_contacts = self.cleaned_data['related_contacts']

        # NB: queries are regrouped to optimise
        relations_map = defaultdict(list)  # per contact relations lists
        for relation in relations.filter(subject_entity=event.id, type__in=_TYPES,
                                         object_entity__in=[contact.id for relationtype, contact in related_contacts]):
            relations_map[relation.object_entity_id].append(relation)

        relations2del = []

        for relationtype, contact in related_contacts:
            relationtype_id = relationtype.id
            contact_relations = relations_map.get(contact.id, ())

            if relationtype_id != constants.REL_OBJ_IS_INVITED_TO:  # => REL_OBJ_CAME_EVENT or REL_OBJ_NOT_CAME_EVENT
                symmetric = _SYMMETRICS[relationtype_id]
                rel2del = find_first(contact_relations, lambda relation: relation.type_id == symmetric, None)

                if rel2del is not None:
                    relations2del.append(rel2del.id)

            if find_first(contact_relations, lambda relation: relation.type_id == relationtype_id, None) is None:
                create_relation(subject_entity=event, type=relationtype, object_entity=contact, user=user)

        if relations2del:
            relations.filter(pk__in=relations2del).delete()


class RelatedOpportunityCreateForm(OpportunityCreateForm):
    def __init__(self, *args, **kwargs):
        # super(RelatedOpportunityCreateForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

        initial = self.initial
        fields  = self.fields

        self.event = event = initial['event']
        contact = initial['contact']

        qs = get_organisation_model().objects.filter(relations__type__in=[REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES],
                                                     relations__object_entity=contact.id,
                                                    )

        description_f = fields.get('description')
        if description_f:
            description_f.initial = ugettext(u'Generated by the event «{}»').format(event)

        if not qs:
            fields['target'].help_text = ugettext(u'(The contact «{}» is not related to an organisation).').format(contact)
        else:
            fields['target'] = ModelChoiceField(label=pgettext('events-opportunity', 'Target organisation'),
                                                queryset=qs, empty_label=None,
                                               )

    def save(self, *args, **kwargs):
        # opp = super(RelatedOpportunityCreateForm, self).save(*args, **kwargs)
        opp = super().save(*args, **kwargs)

        Relation.objects.create(user=self.user, subject_entity=opp,
                                type_id=constants.REL_SUB_GEN_BY_EVENT, object_entity=self.event,
                               )

        return opp
