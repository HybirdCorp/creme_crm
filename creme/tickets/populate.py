# -*- coding: utf-8 -*-

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, SearchConfigItem, BlockConfigItem, RelationBlockItem, ButtonMenuItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.id_generator import generate_string_id_and_save
from creme_core.management.commands.creme_populate import BasePopulator

from tickets.models import Ticket, Priority, Criticity
from tickets.models.status import Status, BASE_STATUS
from tickets.constants import REL_SUB_LINKED_2_TICKET, REL_OBJ_LINKED_2_TICKET


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_LINKED_2_TICKET, _(u'is linked to the ticket')),
                            (REL_OBJ_LINKED_2_TICKET, _(u'(tiket) linked to the entitity'), [Ticket]))

        for pk, name in BASE_STATUS:
            create(Status, pk, name=name, is_custom=False)

        #TODO: use 'start' arg with python 2.6.....
        for i, name in enumerate((_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking'))):
            create(Priority, i + 1, name=name)

        for i, name in enumerate((_('Minor'), _('Major'), _('Feature'), _('Critical'), _('Enhancement'), _('Error'))):
            create(Criticity, i + 1, name=name)

        get_ct = ContentType.objects.get_for_model
        ct_ticket = get_ct(Ticket)

        hf_id = create(HeaderFilter, 'tickets-hf', name=_(u'Ticket view'), entity_type_id=ct_ticket.id, is_custom=False).id
        pref = 'tickets-hfi_'
        create(HeaderFilterItem, pref + 'title',     order=1, name='title',           title=_(u'Title'),            type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'status',    order=2, name='status__name',    title=_(u'Status - Name'),    type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")
        create(HeaderFilterItem, pref + 'priority',  order=3, name='priority__name',  title=_(u'Priority - Name'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="priority__name__icontains")
        create(HeaderFilterItem, pref + 'criticity', order=4, name='criticity__name', title=_(u'Criticity - Name'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="criticity__name__icontains")
        create(HeaderFilterItem, pref + 'cdate',     order=5, name='closing_date',    title=_(u'Closing date'),     type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="closing_date__range")

        SearchConfigItem.create(Ticket, ['title', 'description', 'status__name', 'priority__name', 'criticity__name'])

        #TODO: helper code in creme_config ??? (see 'persons' app)
        rbi = RelationBlockItem.create(REL_OBJ_LINKED_2_TICKET)
        bci = BlockConfigItem(content_type=ct_ticket, block_id=rbi.block_id, order=1, on_portal=False)
        generate_string_id_and_save(BlockConfigItem, [bci], 'creme_config-userbci')

        if 'creme.persons' in settings.INSTALLED_APPS:
            try:
                from persons.models import Contact, Organisation
            except ImportError, e:
                info(str(e))
            else:
                from tickets.buttons import linked_2_ticket_button

                button_id = linked_2_ticket_button.id_
                create(ButtonMenuItem, 'tickets-linked_contact_button', content_type_id=get_ct(Contact).id,      button_id=button_id, order=50)
                create(ButtonMenuItem, 'tickets-linked_orga_button',    content_type_id=get_ct(Organisation).id, button_id=button_id, order=50)

                info("'Persons' app is installed => add button 'Linked to a ticket' to Contact & Organisation")
