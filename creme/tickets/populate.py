# -*- coding: utf-8 -*-

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from creme_core.models import RelationType, SearchConfigItem, BlockConfigItem, RelationBlockItem, ButtonMenuItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from tickets.models import *
from tickets.models.status import BASE_STATUS
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

        hf = HeaderFilter.create(pk='tickets-hf_ticket', name=_(u'Ticket view'), model=Ticket)
        pref = 'tickets-hfi_ticket_'
        create(HeaderFilterItem, pref + 'title',     order=1, name='title',           title=_(u'Title'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'status',    order=2, name='status__name',    title=_(u'Status - Name'),    type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")
        create(HeaderFilterItem, pref + 'priority',  order=3, name='priority__name',  title=_(u'Priority - Name'),  type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="priority__name__icontains")
        create(HeaderFilterItem, pref + 'criticity', order=4, name='criticity__name', title=_(u'Criticity - Name'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="criticity__name__icontains")
        create(HeaderFilterItem, pref + 'cdate',     order=5, name='closing_date',    title=_(u'Closing date'),     type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="closing_date__range")

        hf = HeaderFilter.create(pk='tickets-hf_template', name=_(u'Ticket template view'), model=TicketTemplate)
        pref = 'tickets-hfi_template_'
        create(HeaderFilterItem, pref + 'title',     order=1, name='title',           title=_(u'Title'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'status',    order=2, name='status__name',    title=_(u'Status - Name'),    type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")
        create(HeaderFilterItem, pref + 'priority',  order=3, name='priority__name',  title=_(u'Priority - Name'),  type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="priority__name__icontains")
        create(HeaderFilterItem, pref + 'criticity', order=4, name='criticity__name', title=_(u'Criticity - Name'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="criticity__name__icontains")

        SearchConfigItem.create(Ticket, ['title', 'description', 'status__name', 'priority__name', 'criticity__name'])

        #TODO: helper code in creme_config ??? (see 'persons' app)
        rbi = RelationBlockItem.create(REL_OBJ_LINKED_2_TICKET)
        create(BlockConfigItem, 'tickets-linked2_block',  content_type=ContentType.objects.get_for_model(Ticket), block_id=rbi.block_id, order=1, on_portal=False)

        if 'creme.persons' in settings.INSTALLED_APPS:
            try:
                from persons.models import Contact, Organisation
            except ImportError, e:
                info(str(e))
            else:
                from tickets.buttons import linked_2_ticket_button

                ButtonMenuItem.create(pk='tickets-linked_contact_button', model=Contact,      button=linked_2_ticket_button, order=50)
                ButtonMenuItem.create(pk='tickets-linked_orga_button',    model=Organisation, button=linked_2_ticket_button, order=50)

                info("'Persons' app is installed => add button 'Linked to a ticket' to Contact & Organisation")
