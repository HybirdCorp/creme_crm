# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem, SearchField
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils.meta import get_verbose_field_name
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
        for i, name in enumerate(('Low', 'Normal', 'High', 'Urgent', 'Blocking')):
            create(Priority, i + 1, name=name)

        for i, name in enumerate(('Minor', 'Major', 'Feature', 'Critical', 'Enhancement', 'Error')):
            create(Criticity, i + 1, name=name)

        hf_id = create(HeaderFilter, 'tickets-hf', name=u'Vue de Ticket', entity_type_id=ContentType.objects.get_for_model(Ticket).id, is_custom=False).id
        pref = 'tickets-hfi_'
        create(HeaderFilterItem, pref + 'title',     order=1, name='title',        title=u'Titre',           type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'status',    order=2, name='status',       title=u'Statut',          type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")
        create(HeaderFilterItem, pref + 'priority',  order=3, name='priority',     title=u'Priorité',        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="priority__name__icontains")
        create(HeaderFilterItem, pref + 'criticity', order=4, name='criticity',    title=u'Criticité',       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="criticity__name__icontains")
        create(HeaderFilterItem, pref + 'cdate',     order=5, name='closing_date', title=u'Date de clôture', type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="closing_date__icontains")

        model = Ticket
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['title', 'description', 'status__name', 'priority__name', 'criticity__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
