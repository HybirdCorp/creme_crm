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

from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.buttons import ActionButton
from creme.creme_core.models import RelationType

from . import constants

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class CrmButton(ActionButton):
    __managed_orga = False
    relation_type_id = "OVERRIDE"
    icon_title = _("Relationship")
    icon = "relations"

    def get_managed_orgas(self, entity):
        return (
            Organisation.objects.filter_managed_by_creme()
            .exclude(
                relations_where_is_object__type_id=self.relation_type_id,
                relations_where_is_object__subject_entity=entity,
            )
            .exclude(id=entity.id)
        )

    def ok_4_display(self, entity):
        return self.get_managed_orgas(entity).exists()

    def get_ctypes(self):
        return Contact, Organisation

    def eval_is_enabled(self, context) -> bool:
        return context["can_link"] and context["rtype"].enabled

    def eval_action_data(self, context) -> dict:
        return {
            "organisations": [
                {"value": o.pk, "label": str(o)}
                for o in self.get_managed_orgas(context["object"])
            ],
            "subject_id": context["object"].id,
            "rtype_id": self.relation_type_id,
        }

    def eval_description(self, context):
        rtype = context["rtype"]

        if not context["can_link"]:
            return _("You are not allowed to link this entity")
        elif not rtype.enabled:
            return _("The relationship type «{predicate}» is disabled").format(
                predicate=rtype.predicate
            )
        else:
            return self.description

    def eval_rtype(self, context):
        rtype = RelationType.objects.get(id=self.relation_type_id)
        context["rtype"] = rtype
        return rtype

    def eval_can_link(self, context):
        can_link = context["user"].has_perm_to_link(context["object"])
        context["can_link"] = can_link
        return can_link


class BecomeCustomerButton(CrmButton):
    # id_ = Button.generate_id('persons', 'become_customer')
    id = CrmButton.generate_id("persons", "become_customer")
    action = "persons-hatmenubar-become"
    verbose_name = _("Transform into a customer")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a customer of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_id = constants.REL_SUB_CUSTOMER_SUPPLIER


class BecomeProspectButton(CrmButton):
    # id_ = Button.generate_id('persons', 'become_prospect')
    id = CrmButton.generate_id("persons", "become_prospect")
    action = "persons-hatmenubar-become"
    verbose_name = _("Transform into a prospect")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a prospect of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_id = constants.REL_SUB_PROSPECT


class BecomeSuspectButton(CrmButton):
    # id_ = Button.generate_id('persons', 'become_suspect')
    id = CrmButton.generate_id("persons", "become_suspect")
    action = "persons-hatmenubar-become"
    verbose_name = _("Transform into a suspect")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a suspect of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_id = constants.REL_SUB_SUSPECT


class BecomeInactiveButton(CrmButton):
    # id_ = Button.generate_id('persons', 'become_inactive')
    id = CrmButton.generate_id("persons", "become_inactive")
    action = "persons-hatmenubar-become"
    verbose_name = _("Transform into an inactive customer")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is an inactive customer of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_id = constants.REL_SUB_INACTIVE


class BecomeSupplierButton(CrmButton):
    # id_ = Button.generate_id('persons', 'become_supplier')
    id = CrmButton.generate_id("persons", "become_supplier")
    action = "persons-hatmenubar-become"
    verbose_name = _("Transform into a supplier")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a supplier of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_id = constants.REL_OBJ_CUSTOMER_SUPPLIER


class AddLinkedContactButton(ActionButton):
    # id_ = Button.generate_id('persons', 'add_linked_contact')
    id = CrmButton.generate_id("persons", "add_linked_contact")
    verbose_name = _("Create a related contact")
    description = _(
        "This button displays the creation form for contacts. "
        "The current organisation is pre-selected to be linked to the created contact.\n"
        "It is useful to create employees for example "
        "(it can be done through the employees block too).\n"
        "App: Accounts and Contacts"
    )
    permissions = cperm(Contact)  # TODO: 'persons.addrelated_contact' ??

    def get_ctypes(self):
        return (Organisation,)

    def eval_action_url(self, context) -> str:
        url = reverse("persons__create_related_contact", args=(context["object"].id,))
        return url + f'?callback_url={context["request"].path}'

    def has_perm(self, context) -> bool:
        user = context["user"]
        return user.has_perm_to_link(Contact) and user.has_perm_to_link(
            context["object"]
        )
