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

from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core import auth
from creme.creme_core.buttons import ActionButton
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import Relation, RelationType

from . import constants

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class CrmButton(ActionButton):
    dependencies = (Relation,)  # NB: override 'relation_type_deps' in child classes
    __managed_orgas = False
    # relation_type_id = 'OVERRIDE'
    template_name = 'persons/buttons/become.html'
    action_icon_title = _("Relationship")
    action_icon_name = "relations"
    action_id = "persons-hatmenubar-become"

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        request.user.has_perm_to_link_or_die(entity)

    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)
        # TODO: plural (managed_organisationS, self.__managed_orgaS)
        context['managed_orga'] = self.__managed_orgas
        context['rtype'] = RelationType.objects.get(id=self.relation_type_deps[0])

        return context

    def get_managed_orgas(self, entity, relation_type_id):
        if self.__managed_orgas is False:
            self.__managed_orgas = (
                Organisation.objects.filter_managed_by_creme()
                .exclude(
                    relations_where_is_object__type_id=relation_type_id,
                    relations_where_is_object__subject_entity=entity,
                )
                .exclude(id=entity.id)
            )

        return self.__managed_orgas

    def ok_4_display(self, entity):
        return self.get_managed_orgas(entity, self.relation_type_deps[0]).exists()

    def get_ctypes(self):
        return Contact, Organisation


    def get_context(self, **kwargs):
        context = super().get_context(**kwargs)
        context['description'] = self.get_description(context)
        context['is_allowed'] = context['is_allowed'] and context['rtype'].enabled
        return context

    def get_description(self, context):
        rtype = context["rtype"]

        if not context["can_link"]:
            return _("You are not allowed to link this entity")
        elif not rtype.enabled:
            return _("The relationship type «{predicate}» is disabled").format(
                predicate=rtype.predicate
            )
        else:
            return self.description

    def get_action_data(self, context) -> dict:
        entity = context['object']
        rtype_id = self.relation_type_deps[0]
        orgas = self.get_managed_orgas(entity, rtype_id)

        return {
            "organisations": [
                {"value": o.pk, "label": str(o)}
                for o in orgas
            ],
            "subject_id": entity.id,
            "rtype_id": rtype_id,
        }


class BecomeCustomerButton(CrmButton):
    id = Button.generate_id('persons', 'become_customer')
    verbose_name = _('Transform into a customer')



class BecomeCustomerButton(CrmButton):
    id = Button.generate_id('persons', 'become_customer')
    verbose_name = _("Transform into a customer")
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a customer of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_deps = (constants.REL_SUB_CUSTOMER_SUPPLIER,)


class BecomeProspectButton(CrmButton):
    id = Button.generate_id('persons', 'become_prospect')
    verbose_name = _('Transform into a prospect')
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a prospect of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_deps = (constants.REL_SUB_PROSPECT,)


class BecomeSuspectButton(CrmButton):
    id = Button.generate_id('persons', 'become_suspect')
    verbose_name = _('Transform into a suspect')
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a suspect of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_deps = (constants.REL_SUB_SUSPECT,)


class BecomeInactiveButton(CrmButton):
    id = Button.generate_id('persons', 'become_inactive')
    verbose_name = _('Transform into an inactive customer')
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is an inactive customer of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_deps = (constants.REL_SUB_INACTIVE,)


class BecomeSupplierButton(CrmButton):
    id = Button.generate_id('persons', 'become_supplier')
    verbose_name = _('Transform into a supplier')
    description = _(
        "This button links the current entity to an Organisation managed by Creme, "
        "using the relationship type «is a supplier of».\n"
        "App: Accounts and Contacts"
    )
    relation_type_deps = (constants.REL_OBJ_CUSTOMER_SUPPLIER,)


class AddLinkedContactButton(ActionButton):
    id = Button.generate_id("persons", "add_linked_contact")
    verbose_name = _("Create a related contact")
    description = _(
        "This button displays the creation form for contacts. "
        "The current organisation is pre-selected to be linked to the created contact.\n"
        "It is useful to create employees for example "
        "(it can be done through the employees block too).\n"
        "App: Accounts and Contacts"
    )
    permissions = [
        auth.build_creation_perm(Contact),  # TODO: 'persons.addrelated_contact' ??
        auth.build_link_perm(Contact),
    ]
    action_icon_title = _("Linked Contact")
    action_icon_name = "contact"

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        user = request.user
        user.has_perm_to_link_or_die(entity)

    def get_ctypes(self):
        return (Organisation,)

    def get_action_url(self, context) -> str:
        url = reverse("persons__create_related_contact", args=(context["object"].id,))
        return url + f'?callback_url={context["request"].path}'


class TransformIntoUserButton(Button):
    id = Button.generate_id('persons', 'transform_into_user')
    verbose_name = _('Transform into a user')
    description = _(
        "This button allows to create a user corresponding to the current Contact. "
        "A Contact is automatically created when you create a user; with "
        "this button you can create the user linked to an existing Contact "
        "(you don't have to merge the existing Contact with the one created by "
        "the user creation form).\n"
        "Only superusers can use this button.\n"
        "App: Accounts and Contacts"
    )
    template_name = 'persons/buttons/contact-as-user.html'
    permissions = auth.SUPERUSER_PERM

    def ok_4_display(self, entity):
        return entity.is_user_id is None

    def get_ctypes(self):
        return (Contact,)
