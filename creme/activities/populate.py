# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, BlockConfigItem, ButtonMenuItem, SearchConfigItem, SearchField
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from activities.models import Activity, ActivityType, PhoneCallType, TaskStatus
from activities.blocks import future_activities_block, past_activities_block
from activities.buttons import add_meeting_button, add_phonecall_button, add_task_button
from activities.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_LINKED_2_ACTIVITY, _(u"related to the activity")),
                            (REL_OBJ_LINKED_2_ACTIVITY, _(u"related to"))) #[Activity and inherited klass ??]
        #RelationType.create((REL_SUB_RDV,              u'prend part au rendez-vous'),
                            #(REL_OBJ_RDV,              u'a pour participant'))
        #RelationType.create((REL_SUB_CALL,             u"participe a l'appel"),
                            #(REL_OBJ_CALL,             u'concerne'))
        RelationType.create((REL_SUB_ACTIVITY_SUBJECT, _(u"is subject of the activity")),
                            (REL_OBJ_ACTIVITY_SUBJECT, _(u'is to subject')))
        RelationType.create((REL_SUB_PART_2_ACTIVITY,  _(u"participates to the activity")),
                            (REL_OBJ_PART_2_ACTIVITY,  _(u'has as participant')))


        create(PhoneCallType, 1, name=_(u"Incoming"), description=_(u"Incoming call"))
        create(PhoneCallType, 2, name=_(u"Outgoing"), description=_(u"Outgoing call"))
        create(PhoneCallType, 3, name=_(u"Other"),    description=_(u"Example: a conference"))
        
    
        create(TaskStatus, 1, name=_(u"Prévue"), description=_(u"Prévue"))
        create(TaskStatus, 2, name=_(u"En cours"), description=_(u"En cours"))
        create(TaskStatus, 3, name=_(u"Finie"), description=_(u"Finie"))
        create(TaskStatus, 4, name=_(u"En retard"), description=_(u"En retard"))

        create(ActivityType, ACTIVITYTYPE_TASK,      name=_(u"Task"),            color="987654", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_MEETING,   name=_(u"Meeting"),         color="456FFF", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_PHONECALL, name=_(u"Phone call"),      color="A24BBB", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_GATHERING, name=_(u"Gathering"),       color="F23C39", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_SHOW,      name=_(u"Show"),            color="8DE501", default_day_duration=1, default_hour_duration="00:00:00")
        create(ActivityType, ACTIVITYTYPE_DEMO,      name=_(u"Demonstration"),   color="4EEF65", default_day_duration=0, default_hour_duration="01:00:00")
        create(ActivityType, ACTIVITYTYPE_INDISPO,   name=_(u"Indisponibility"), color="CC0000", default_day_duration=1, default_hour_duration="00:00:00")

        hf_id = create(HeaderFilter, 'activities-hf', name=_(u"Activity view"), entity_type_id=ContentType.objects.get_for_model(Activity).id, is_custom=False).id
        pref = 'activities-hfi_'
        create(HeaderFilterItem, pref + 'title', order=1, name='title', title=_(u'Name'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'start', order=2, name='start', title=_(u'Start'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="start__range")
        create(HeaderFilterItem, pref + 'end',   order=3, name='end',   title=_(u'End'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="end__range")
        create(HeaderFilterItem, pref + 'type',  order=4, name='type',  title=_(u'Type'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="type__name__icontains")

        create(BlockConfigItem, 'activities-future_activities_block', content_type=None, block_id=future_activities_block.id_, order=20, on_portal=False)
        create(BlockConfigItem, 'activities-past_activities_block',   content_type=None, block_id=past_activities_block.id_,   order=21, on_portal=False)

        create(ButtonMenuItem, 'activities-add_meeting_button',   content_type=None, button_id=add_meeting_button.id_,   order=10)
        create(ButtonMenuItem, 'activities-add_phonecall_button', content_type=None, button_id=add_phonecall_button.id_, order=11)
        create(ButtonMenuItem, 'activities-add_task_button', content_type=None, button_id=add_task_button.id_, order=12)

        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(Activity).id)
        SCI_pk = sci.pk
        sci_fields = ['title', 'description', 'type__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(Activity, field), order=i, search_config_item_id=SCI_pk)


