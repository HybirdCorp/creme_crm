################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core import forms as core_forms
from creme.creme_core.models import Relation

from .. import constants


class AddContactsToEventForm(core_forms.CremeForm):
    related_contacts = core_forms.MultiRelationEntityField(
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
        create_relation = relations.safe_create

        related_contacts = self.cleaned_data['related_contacts']

        # NB: queries are regrouped to optimise
        relations_map = defaultdict(list)  # per contact relations lists
        for relation in relations.filter(
            subject_entity=event.id,
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

            if relationtype_id != constants.REL_OBJ_IS_INVITED_TO:
                symmetric = self.symmetric_rtype_ids[relationtype_id]
                rel2del = next(
                    (rel for rel in contact_relations if rel.type_id == symmetric),
                    None,  # default
                )

                if rel2del is not None:
                    relations2del.append(rel2del.id)

            if not any(rel.type_id == relationtype_id for rel in contact_relations):
                create_relation(
                    subject_entity=event,
                    type=relationtype,
                    object_entity=contact,
                    user=user,
                )

        if relations2del:
            relations.filter(pk__in=relations2del).delete()

        return event
