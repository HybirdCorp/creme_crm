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

from collections import defaultdict

from django.forms import DateTimeField, ModelChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm, CremeForm, MultiRelationEntityField
from creme_core.forms.widgets import DateTimeWidget
from creme_core.forms.validators import validate_linkable_entities
from creme_core.utils import find_first

from persons.models import Organisation
from persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES

from opportunities.forms.opportunity import OpportunityCreateForm

from events.models import Event
from events.constants import *


class EventForm(CremeEntityForm):
    start_date = DateTimeField(label=_(u'Start date'), widget=DateTimeWidget)
    end_date   = DateTimeField(label=_(u'End date'), required=False, widget=DateTimeWidget)#TODO: start_date > end_date ?

    class Meta(CremeEntityForm.Meta):
        model = Event


_SYMMETRICS = {
        REL_OBJ_CAME_EVENT:     REL_OBJ_NOT_CAME_EVENT,
        REL_OBJ_NOT_CAME_EVENT: REL_OBJ_CAME_EVENT,
    }

_TYPES = [REL_OBJ_IS_INVITED_TO, REL_OBJ_CAME_EVENT, REL_OBJ_NOT_CAME_EVENT]

class AddContactsToEventForm(CremeForm):
    related_contacts = MultiRelationEntityField(allowed_rtypes=_TYPES, label=_(u'Related contacts'))

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('instance')
        super(AddContactsToEventForm, self).__init__(*args, **kwargs)

    def clean_related_contacts(self):
        #Because of the optimisations, the save() algo will be wrong with a contact that is present twice.
        related_contacts = self.cleaned_data['related_contacts']
        contacts_set = set()

        for relationtype, contact in related_contacts:
            if contact.id in contacts_set:
                raise ValidationError(ugettext(u'Contact %s is present twice.') % contact)

            contacts_set.add(contact.id)

        validate_linkable_entities([contact for relationtype, contact in related_contacts], self.user)

        return related_contacts

    def save(self):
        #BEWARE: chosen contacts can have already relations with the event ;
        #        we avoid several 'REL_OBJ_IS_INVITED_TO' relations,
        #        'REL_OBJ_CAME_EVENT' override existing 'REL_OBJ_NOT_CAME_EVENT' relations etc...
        event = self.event
        user  = self.user
        relations = Relation.objects
        create_relation = relations.create

        related_contacts = self.cleaned_data['related_contacts']

        #NB: queries are regrouped to optimise
        relations_map = defaultdict(list) #per contact relations lists
        for relation in relations.filter(subject_entity=event.id, type__in=_TYPES,
                                         object_entity__in=[contact.id for relationtype, contact in related_contacts]):
            relations_map[relation.object_entity_id].append(relation)

        relations2del = []

        for relationtype, contact in related_contacts:
            relationtype_id = relationtype.id
            contact_relations = relations_map.get(contact.id, ())

            if relationtype_id != REL_OBJ_IS_INVITED_TO: # => REL_OBJ_CAME_EVENT or REL_OBJ_NOT_CAME_EVENT
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
        super(RelatedOpportunityCreateForm, self).__init__(*args, **kwargs)

        initial = self.initial
        fields  = self.fields

        self.event = initial['event']
        contact    = initial['contact']

        qs = Organisation.objects.filter(relations__type__in=[REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES],
                                         relations__object_entity=contact.id)

        fields['description'].initial = ugettext(u'Generated by the event "%s"') % self.event

        if not qs:
            fields['target_orga'].help_text = ugettext(u'(The contact "%s" is not related to an organisation).') % contact
        else:
            fields['target_orga'] = ModelChoiceField(label=pgettext('events-opportunity', 'Target organisation'), queryset=qs, empty_label=None)

    def save(self, *args, **kwargs):
        opp = super(RelatedOpportunityCreateForm, self).save(*args, **kwargs)

        Relation.objects.create(user=self.user, subject_entity=opp,
                                type_id=REL_SUB_GEN_BY_EVENT, object_entity=self.event
                               )

        return opp
