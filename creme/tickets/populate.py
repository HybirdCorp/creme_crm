# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from tickets.models.ticket import Ticket
from tickets.models.status import Status, BASE_STATUS
from tickets.models.priority import Priority
from tickets.models.criticity import Criticity


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        for pk, name in BASE_STATUS:
            create(Status, pk, name=name, deletable=False)

        #TODO: use 'start' arg with python 2.6.....
        for i, name in enumerate((_('Low'), _('Normal'), _('High'), _('Urgent'), _('Blocking'))):
            create(Priority, i + 1, name=name)

        for i, name in enumerate((_('Minor'), _('Major'), _('Feature'), _('Critical'), _('Enhancement'), _('Error'))):
            create(Criticity, i + 1, name=name)

        hf_id = create(HeaderFilter, 'tickets-hf', name=_(u'Ticket view'), entity_type_id=ContentType.objects.get_for_model(Ticket).id, is_custom=False).id
        pref = 'tickets-hfi_'
        create(HeaderFilterItem, pref + 'title',     order=1, name='title',        title=_(u'Title'),        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'status',    order=2, name='status',       title=_(u'Status'),       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")
        create(HeaderFilterItem, pref + 'priority',  order=3, name='priority',     title=_(u'Priority'),     type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="priority__name__icontains")
        create(HeaderFilterItem, pref + 'criticity', order=4, name='criticity',    title=_(u'Criticity'),    type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="criticity__name__icontains")
        create(HeaderFilterItem, pref + 'cdate',     order=5, name='closing_date', title=_(u'Closing date'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="closing_date__icontains")

        SearchConfigItem.create(Ticket, ['title', 'description', 'status__name', 'priority__name', 'criticity__name'])

