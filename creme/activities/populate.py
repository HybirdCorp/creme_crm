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
from creme_core.models import RelationType, BlockConfigItem, ButtonMenuItem
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from activities.models import Activity, ActivityType, PhoneCallType
from activities.blocks import future_activities_block, past_activities_block
from activities.buttons import add_meeting_button, add_phonecall_button
from activities.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_LINKED_2_ACTIVITY, u"relié à l'activité"),
                            (REL_OBJ_LINKED_2_ACTIVITY, u"relié à")) #[Activity and inherited klass ??]
        #RelationType.create((REL_SUB_RDV,              u'prend part au rendez-vous'),
                            #(REL_OBJ_RDV,              u'a pour participant'))
        #RelationType.create((REL_SUB_CALL,             u"participe a l'appel"),
                            #(REL_OBJ_CALL,             u'concerne'))
        RelationType.create((REL_SUB_ACTIVITY_SUBJECT, u"est sujet de l'activité"),
                            (REL_OBJ_ACTIVITY_SUBJECT, u'a pour sujet'),            display_with_other=False)
        RelationType.create((REL_SUB_PART_2_ACTIVITY,  u"participe à l'activité"),
                            (REL_OBJ_PART_2_ACTIVITY,  u'a pour participant'),      display_with_other=False)


        create(PhoneCallType, 1, name=_(u"Entrant"), description=_(u"Appel entrant"))
        create(PhoneCallType, 2, name=_(u"Sortant"), description=_(u"Appel sortant"))
        create(PhoneCallType, 3, name=_(u"Autre"),   description=_(u"Exemple: une conférence"))

        create(ActivityType, ACTIVITYTYPE_TASK,      name=_(u"Tâche"),              color="987654", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_MEETING,   name=_(u"Rendez-vous"),        color="456FFF", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_PHONECALL, name=_(u"Appel Téléphonique"), color="A24BBB", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_GATHERING, name=_(u"Réunion"),            color="F23C39", default_day_duration=0, default_hour_duration="00:15:00")
        create(ActivityType, ACTIVITYTYPE_SHOW,      name=_(u"Salon"),              color="8DE501", default_day_duration=1, default_hour_duration="00:00:00")
        create(ActivityType, ACTIVITYTYPE_DEMO,      name=_(u"Démonstration"),      color="4EEF65", default_day_duration=0, default_hour_duration="01:00:00")
        create(ActivityType, ACTIVITYTYPE_INDISPO,   name=_(u"Indisponible"),       color="CC0000", default_day_duration=1, default_hour_duration="00:00:00")

        hf_id = create(HeaderFilter, 'activities-hf', name=u"Vue d'Activité", entity_type_id=ContentType.objects.get_for_model(Activity).id, is_custom=False).id
        pref = 'activities-hfi_'
        create(HeaderFilterItem, pref + 'title', order=1, name='title', title=_(u'Nom'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'start', order=2, name='start', title=_(u'Début'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="start__range")
        create(HeaderFilterItem, pref + 'end',   order=3, name='end',   title=_(u'Fin'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="end__range")
        create(HeaderFilterItem, pref + 'type',  order=4, name='type',  title=_(u'Type'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="type__name__icontains")

        create(BlockConfigItem, 'activities-future_activities_block', content_type=None, block_id=future_activities_block.id_, order=20, on_portal=False)
        create(BlockConfigItem, 'activities-past_activities_block',   content_type=None, block_id=past_activities_block.id_,   order=21, on_portal=False)

        create(ButtonMenuItem, 'activities-add_meeting_button',   content_type=None, button_id=add_meeting_button.id_,   order=10)
        create(ButtonMenuItem, 'activities-add_phonecall_button', content_type=None, button_id=add_phonecall_button.id_, order=11)
