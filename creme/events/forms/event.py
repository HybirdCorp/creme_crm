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

# import warnings
from collections import defaultdict

from django.forms import ValidationError  # ModelChoiceField
# from django.utils.translation import gettext
# from django.utils.translation import pgettext
from django.utils.translation import gettext_lazy as _

# from creme.opportunities.forms.opportunity import OpportunityCreationForm
# from creme.persons import get_organisation_model
# from creme.persons.constants import REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES
from creme.creme_core.forms import (  # CremeEntityForm
    CremeForm,
    MultiRelationEntityField,
)
from creme.creme_core.models import Relation
from creme.creme_core.utils import find_first

from .. import constants  # get_event_model

# class EventForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = get_event_model()
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('EventForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# _SYMMETRICS = {
#     constants.REL_OBJ_CAME_EVENT:     constants.REL_OBJ_NOT_CAME_EVENT,
#     constants.REL_OBJ_NOT_CAME_EVENT: constants.REL_OBJ_CAME_EVENT,
# }

# _TYPES = [
#     constants.REL_OBJ_IS_INVITED_TO,
#     constants.REL_OBJ_CAME_EVENT,
#     constants.REL_OBJ_NOT_CAME_EVENT,
# ]


class AddContactsToEventForm(CremeForm):
    related_contacts = MultiRelationEntityField(
        # allowed_rtypes=_TYPES,
        allowed_rtypes=[
            constants.REL_OBJ_IS_INVITED_TO,
            constants.REL_OBJ_CAME_EVENT,
            constants.REL_OBJ_NOT_CAME_EVENT,
        ],
        label=_('Related contacts'),
    )

    error_messages = {
        'duplicates': _('Contact %(contact)s is present twice.'),
    }

    symmetric_rtype_ids = {
        constants.REL_OBJ_CAME_EVENT:     constants.REL_OBJ_NOT_CAME_EVENT,
        constants.REL_OBJ_NOT_CAME_EVENT: constants.REL_OBJ_CAME_EVENT,
    }

    def __init__(self, instance, *args, **kwargs):
        self.event = instance
        super().__init__(*args, **kwargs)

        # TODO: factorise (_RelationsCreateForm in creme_core) ??
        relations_field = self.fields['related_contacts']
        relations_field.initial = [(relations_field.allowed_rtypes.all()[0], None)]

    def clean_related_contacts(self):
        # Because of the optimisations, the save() algo will be wrong with a
        # contact that is present twice.
        related_contacts = self.cleaned_data['related_contacts']
        contacts_set = set()

        for relationtype, contact in related_contacts:
            if contact.id in contacts_set:
                raise ValidationError(
                    self.error_messages['duplicates'],
                    params={'contact': contact},
                    code='duplicates',
                )

            contacts_set.add(contact.id)

        return related_contacts

    def save(self):
        # BEWARE: chosen contacts can have already relations with the event ;
        #   we avoid several 'REL_OBJ_IS_INVITED_TO' relations,
        #   'REL_OBJ_CAME_EVENT' override existing 'REL_OBJ_NOT_CAME_EVENT' relations etc...
        event = self.event
        user = self.user
        relations = Relation.objects
        create_relation = relations.create

        related_contacts = self.cleaned_data['related_contacts']

        # NB: queries are regrouped to optimise
        relations_map = defaultdict(list)  # per contact relations lists
        for relation in relations.filter(
            subject_entity=event.id,
            # type__in=_TYPES,
            type__in=self.fields['related_contacts'].allowed_rtypes,
            object_entity__in=[
                contact.id for relationtype, contact in related_contacts
            ],
        ):
            relations_map[relation.object_entity_id].append(relation)

        relations2del = []

        for relationtype, contact in related_contacts:
            relationtype_id = relationtype.id
            contact_relations = relations_map.get(contact.id, ())

            # REL_OBJ_CAME_EVENT or REL_OBJ_NOT_CAME_EVENT
            if relationtype_id != constants.REL_OBJ_IS_INVITED_TO:
                # symmetric = _SYMMETRICS[relationtype_id]
                symmetric = self.symmetric_rtype_ids[relationtype_id]
                rel2del = find_first(
                    contact_relations,
                    lambda relation: relation.type_id == symmetric,
                    None,
                )

                if rel2del is not None:
                    relations2del.append(rel2del.id)

            if find_first(
                    contact_relations,
                    lambda relation: relation.type_id == relationtype_id,
                    None
            ) is None:
                create_relation(
                    subject_entity=event,
                    type=relationtype,
                    object_entity=contact,
                    user=user,
                )

        if relations2del:
            relations.filter(pk__in=relations2del).delete()

        return event


# class RelatedOpportunityCreateForm(OpportunityCreationForm):
#     def __init__(self, event, contact, *args, **kwargs):
#         warnings.warn('RelatedOpportunityCreateForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#         fields = self.fields
#         self.event = event
#
#         qs = get_organisation_model().objects.filter(
#             relations__type__in=[REL_OBJ_EMPLOYED_BY, REL_OBJ_MANAGES],
#             relations__object_entity=contact.id,
#         )
#
#         description_f = fields.get('description')
#         if description_f:
#             description_f.initial = gettext('Generated by the event «{}»').format(event)
#
#         if not qs:
#             fields['target'].help_text = gettext(
#                 '(The contact «{}» is not related to an organisation).'
#             ).format(contact)
#         else:
#             fields['target'] = ModelChoiceField(
#                 label=pgettext('events-opportunity', 'Target organisation'),
#                 queryset=qs,
#                 empty_label=None,
#             )
#
#     def _get_relations_to_create(self):
#         instance = self.instance
#
#         return super()._get_relations_to_create().append(Relation(
#             user=instance.user,
#             subject_entity=instance,
#             type_id=constants.REL_SUB_GEN_BY_EVENT,
#             object_entity=self.event,
#         ))
