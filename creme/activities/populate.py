# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _, pgettext

from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, ButtonMenuItem, SearchConfigItem,
        BlockDetailviewLocation, BlockPortalLocation, SettingValue,
        HeaderFilter, EntityFilter, EntityFilterCondition)
from creme.creme_core.utils import create_if_needed

from creme.persons.models import Contact, Organisation

from .blocks import (participants_block, subjects_block, future_activities_block,
                     past_activities_block, related_calendar_block)
from .buttons import add_activity_button, add_meeting_button, add_phonecall_button, add_task_button
from .constants import *
from .models import ActivityType, ActivitySubType, Activity, Status, Calendar
from .setting_keys import review_key, auto_subjects_key


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        create_rtype = RelationType.create
        create_rtype((REL_SUB_LINKED_2_ACTIVITY, _(u"related to the activity")),
                     (REL_OBJ_LINKED_2_ACTIVITY, _(u"(activity) related to"),    [Activity])
                    )
        rt_obj_activity_subject = \
            create_rtype((REL_SUB_ACTIVITY_SUBJECT, _(u"is subject of the activity"), [Contact, Organisation]),
                         (REL_OBJ_ACTIVITY_SUBJECT, _(u'(activity) is to subject'),   [Activity])
                        )[1]
        rt_obj_part_2_activity = \
            create_rtype((REL_SUB_PART_2_ACTIVITY, _(u"participates to the activity"),  [Contact]),
                         (REL_OBJ_PART_2_ACTIVITY, _(u'(activity) has as participant'), [Activity]),
                         is_internal=True
                        )[1]

        create_if_needed(Status, {'pk': STATUS_PLANNED},     name=pgettext('activities-status', 'Planned'),     description=pgettext('activities-status', 'Planned'),     is_custom=False)
        create_if_needed(Status, {'pk': STATUS_IN_PROGRESS}, name=pgettext('activities-status', 'In progress'), description=pgettext('activities-status', 'In progress'), is_custom=False)
        create_if_needed(Status, {'pk': STATUS_DONE},        name=pgettext('activities-status', 'Done'),        description=pgettext('activities-status', 'Done'),        is_custom=False)
        create_if_needed(Status, {'pk': STATUS_DELAYED},     name=pgettext('activities-status', 'Delayed'),     description=pgettext('activities-status', 'Delayed'),     is_custom=False)
        create_if_needed(Status, {'pk': STATUS_CANCELLED},   name=pgettext('activities-status', 'Cancelled'),   description=pgettext('activities-status', 'Cancelled'),   is_custom=False)

        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_TASK},      name=_(u"Task"),            default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        meeting_type = \
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_MEETING},   name=_(u"Meeting"),         default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        phone_call_type = \
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_PHONECALL}, name=_(u"Phone call"),      default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_GATHERING}, name=_(u"Gathering"),       default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_SHOW},      name=_(u"Show"),            default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_DEMO},      name=_(u"Demonstration"),   default_day_duration=0, default_hour_duration="01:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': ACTIVITYTYPE_INDISPO},   name=_(u"Indisponibility"), default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)

        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_MEETING_MEETING},       name=_('Meeting'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_MEETING_QUALIFICATION}, name=_('Qualification'),                      type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_MEETING_REVIVAL},       name=_('Revival'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_MEETING_NETWORK},       name=_('Network'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_MEETING_OTHER},         name=pgettext('activities-meeting', 'Other'), type=meeting_type, is_custom=False)

        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_PHONECALL_INCOMING},   name=_('Incoming'),   type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_PHONECALL_OUTGOING},   name=_('Outgoing'),   type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': ACTIVITYSUBTYPE_PHONECALL_CONFERENCE}, name=_('Conference'), type=phone_call_type, is_custom=False)

        HeaderFilter.create(pk='activities-hf_activity', name=_(u'Activity view'), model=Activity,
                            cells_desc=[(EntityCellRegularField, {'name': 'start'}),
                                        (EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'type'}),
                                        EntityCellRelation(rtype=rt_obj_part_2_activity),
                                        EntityCellRelation(rtype=rt_obj_activity_subject),
                                        (EntityCellRegularField, {'name': 'user'}),
                                        (EntityCellRegularField, {'name': 'end'}),
                                       ]
                           )

        for pk, name, atype_id in ((EFILTER_MEETINGS,   _(u"Meetings"),    ACTIVITYTYPE_MEETING),
                                   (EFILTER_PHONECALLS, _(u"Phone calls"), ACTIVITYTYPE_PHONECALL),
                                   (EFILTER_TASKS,      _(u"Tasks"),       ACTIVITYTYPE_TASK),
                                  ):
            efilter = EntityFilter.create(pk, name=name, model=Activity, is_custom=False)
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=Activity,
                                                                        operator=EntityFilterCondition.EQUALS,
                                                                        name='type',
                                                                        values=[atype_id],
                                                                       ),
                                   ]
                                  )

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Activity)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,           order=40,  zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=related_calendar_block.id_, order=90,  zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=participants_block.id_,           order=100, zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=subjects_block.id_,               order=120, zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=properties_block.id_,             order=450, zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=relations_block.id_,              order=500, zone=BlockDetailviewLocation.LEFT,  model=Activity)
        BlockDetailviewLocation.create(block_id=history_block.id_,                order=20,  zone=BlockDetailviewLocation.RIGHT, model=Activity)

        if 'creme.assistants' in settings.INSTALLED_APPS:
            logger.info('Assistants app is installed => we use the activities blocks on detail views')

            from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=Activity)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=Activity)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=Activity)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT, model=Activity)


        future_id = future_activities_block.id_
        past_id   = past_activities_block.id_
        BlockDetailviewLocation.create(block_id=future_id, order=20, zone=BlockDetailviewLocation.RIGHT, model=Contact)
        BlockDetailviewLocation.create(block_id=past_id,   order=21, zone=BlockDetailviewLocation.RIGHT, model=Contact)
        BlockDetailviewLocation.create(block_id=future_id, order=20, zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockDetailviewLocation.create(block_id=past_id,   order=21, zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockPortalLocation.create(app_name='persons',    block_id=future_id, order=20)
        BlockPortalLocation.create(app_name='persons',    block_id=past_id,   order=21)
        BlockPortalLocation.create(app_name='creme_core', block_id=future_id, order=20)
        BlockPortalLocation.create(app_name='creme_core', block_id=past_id,   order=21)

        create_button = ButtonMenuItem.create_if_needed
        create_button('activities-add_activity_button',  model=None, button=add_activity_button,  order=10)
        create_button('activities-add_meeting_button',   model=None, button=add_meeting_button,   order=11)
        create_button('activities-add_phonecall_button', model=None, button=add_phonecall_button, order=12)
        create_button('activities-add_task_button',      model=None, button=add_task_button,      order=13)

        SearchConfigItem.create_if_needed(Activity, ['title', 'description', 'type__name'])

        for user in User.objects.all():
            Calendar.get_user_default_calendar(user)

        #sk = SettingKey.create(pk=DISPLAY_REVIEW_ACTIVITIES_BLOCKS,
                               #description=_(u"Display minutes information in activities blocks"),
                               #app_label='activities', type=SettingKey.BOOL,
                              #)
        #SettingValue.create_if_needed(key=sk, user=None, value=True)
        SettingValue.create_if_needed(key=review_key, user=None, value=True)

        #sk = SettingKey.create(pk=SETTING_AUTO_ORGA_SUBJECTS,
                               #description=_(u"Add automatically the organisations of the participants as activities subjects"),
                               #app_label='activities', type=SettingKey.BOOL,
                              #)
        #SettingValue.create_if_needed(key=sk, user=None, value=True)
        SettingValue.create_if_needed(key=auto_subjects_key, user=None, value=True)
