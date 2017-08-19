# -*- coding: utf-8 -*-

import warnings

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.bricks import Brick, QuerysetBrick
from creme.creme_core.utils.db import populate_related

from .bricks import (
    Contact, Organisation, Address, _get_address_field_names,
    ManagersBrick as ManagersBlock,
    EmployeesBrick as EmployeesBlock,
)

if apps.is_installed('creme.activities'):
    from .bricks import NeglectedOrganisationsBrick as NeglectedOrganisationsBlock

warnings.warn('persons.blocks is deprecated ; use persons.bricks instead.', DeprecationWarning)


class AddressBlock(Brick):
    id_           = Brick.generate_id('persons', 'address')
    dependencies  = (Address,)
    verbose_name  = _(u'Addresses (detailed)')
    template_name = 'persons/templatetags/block_address.html'
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        person = context['object']
        model = person.__class__
        is_hidden = context['fields_configs'].get_4_model(model).is_field_hidden

        def prepare_address(attr_name):
            display_button = display_content = False

            try:
                addr = getattr(person, attr_name)
            except AttributeError:
                addr = Address()
            else:
                if is_hidden(model._meta.get_field(attr_name)):
                    if addr is None:
                        addr = Address()
                elif addr is None:
                    addr = Address()
                    display_button = True
                else:
                    display_content = True

            addr.display_button  = display_button
            addr.display_content = display_content

            addr.owner = person  # NB: avoids a query (per address) for credentials.

            return addr

        populate_related((person,), ['billing_address', 'shipping_address'])
        b_address = prepare_address('billing_address')
        s_address = prepare_address('shipping_address')

        colspan = 0
        if b_address.display_content: colspan += 3
        if s_address.display_content: colspan += 3
        if not colspan: colspan = 1

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (
                    #                 self.id_, person.pk,
                    #             ),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, person.id)),
                    b_address=b_address,
                    s_address=s_address,
                    field_names=_get_address_field_names(),  # TODO: cache in context ??
                    address_model=Address,  # For fields' verbose name
                    colspan=colspan,
        ))


class OtherAddressBlock(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('persons', 'other_address')
    dependencies  = (Address,)
    verbose_name  = _(u'Other addresses (detailed)')
    template_name = 'persons/templatetags/block_other_address.html'
    target_ctypes = (Contact, Organisation)
    page_size     = 1

    def detailview_display(self, context):
        person = context['object']

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    person.other_addresses,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (
                    #                 self.id_, person.pk,
                    #             ),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, person.id)),
                    field_names=_get_address_field_names(),
                    ct_id=ContentType.objects.get_for_model(Address).id,
        ))


# contact_coord_block   = ContactCoordinatesBlock()
# orga_coord_block      = OrgaCoordinatesBlock()
address_block         = AddressBlock()
other_address_block   = OtherAddressBlock()
managers_block        = ManagersBlock()
employees_block       = EmployeesBlock()
neglected_orgas_block = NeglectedOrganisationsBlock()

block_list = (
#    contact_coord_block,
#    orga_coord_block,
    address_block,
    other_address_block,
    managers_block,
    employees_block,
    neglected_orgas_block,
)
