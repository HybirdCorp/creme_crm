# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _, pgettext

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, ButtonMenuItem, SearchConfigItem,
        BlockDetailviewLocation, BlockPortalLocation, SettingValue,
        HeaderFilter, EntityFilter, EntityFilterCondition)
from creme.creme_core.utils import create_if_needed

from creme import persons
from creme.persons.constants import FILTER_CONTACT_ME

from . import get_activity_model, bricks, buttons, constants, setting_keys
from .models import ActivityType, ActivitySubType, Status, Calendar


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_LINKED_2_ACTIVITY).exists()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        Activity = get_activity_model()

        # ---------------------------
        create_rtype = RelationType.create
        create_rtype((constants.REL_SUB_LINKED_2_ACTIVITY, _(u'related to the activity')),
                     (constants.REL_OBJ_LINKED_2_ACTIVITY, _(u'(activity) related to'),    [Activity]),
                     minimal_display=(True, False),
                    )
        rt_obj_activity_subject = \
            create_rtype((constants.REL_SUB_ACTIVITY_SUBJECT, _(u'is subject of the activity'), [Contact, Organisation]),
                         (constants.REL_OBJ_ACTIVITY_SUBJECT, _(u'(activity) is to subject'),   [Activity]),
                         minimal_display=(True, False),
                        )[1]
        rt_obj_part_2_activity = \
            create_rtype((constants.REL_SUB_PART_2_ACTIVITY, _(u'participates to the activity'),  [Contact]),
                         (constants.REL_OBJ_PART_2_ACTIVITY, _(u'(activity) has as participant'), [Activity]),
                         is_internal=True,
                         minimal_display=(True, False),
                        )[1]

        # ---------------------------
        create_if_needed(Status, {'pk': constants.STATUS_PLANNED},     name=pgettext('activities-status', u'Planned'),     description=pgettext('activities-status', u'Planned'),     is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_IN_PROGRESS}, name=pgettext('activities-status', u'In progress'), description=pgettext('activities-status', u'In progress'), is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_DONE},        name=pgettext('activities-status', u'Done'),        description=pgettext('activities-status', u'Done'),        is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_DELAYED},     name=pgettext('activities-status', u'Delayed'),     description=pgettext('activities-status', u'Delayed'),     is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_CANCELLED},   name=pgettext('activities-status', u'Cancelled'),   description=pgettext('activities-status', u'Cancelled'),   is_custom=False)

        # ---------------------------
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_TASK},      name=_(u'Task'),           default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        meeting_type = \
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_MEETING},   name=_(u'Meeting'),        default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        phone_call_type = \
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_PHONECALL}, name=_(u'Phone call'),     default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_GATHERING}, name=_(u'Gathering'),      default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_SHOW},      name=_(u'Show'),           default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_DEMO},      name=_(u'Demonstration'),  default_day_duration=0, default_hour_duration="01:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_INDISPO},   name=_(u'Unavailability'), default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)

        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_MEETING},       name=_(u'Meeting'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION}, name=_(u'Qualification'),                      type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_REVIVAL},       name=_(u'Revival'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_NETWORK},       name=_(u'Network'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_OTHER},         name=pgettext('activities-meeting', u'Other'), type=meeting_type, is_custom=False)

        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING},   name=_(u'Incoming'),          type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING},   name=_(u'Outgoing'),          type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_CONFERENCE}, name=_(u'Conference'),        type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_FAILED},     name=_(u'Outgoing - Failed'), type=phone_call_type, is_custom=False)

        # ---------------------------
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_ACTIVITY, name=_(u'Activity view'), model=Activity,
                            cells_desc=[(EntityCellRegularField, {'name': 'start'}),
                                        (EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'type'}),
                                        EntityCellRelation(model=Activity, rtype=rt_obj_part_2_activity),
                                        EntityCellRelation(model=Activity, rtype=rt_obj_activity_subject),
                                        (EntityCellRegularField, {'name': 'user'}),
                                        (EntityCellRegularField, {'name': 'end'}),
                                       ],
                           )

        # ---------------------------
        create_efilter = EntityFilter.create

        for pk, name, atype_id in ((constants.EFILTER_MEETINGS,   _(u'Meetings'),    constants.ACTIVITYTYPE_MEETING),
                                   (constants.EFILTER_PHONECALLS, _(u'Phone calls'), constants.ACTIVITYTYPE_PHONECALL),
                                   (constants.EFILTER_TASKS,      _(u'Tasks'),       constants.ACTIVITYTYPE_TASK),
                                  ):
            create_efilter(pk, name=name, model=Activity, is_custom=False, user='admin',
                           conditions=[EntityFilterCondition.build_4_field(model=Activity,
                                             operator=EntityFilterCondition.EQUALS,
                                             name='type',
                                             values=[atype_id],
                                         ),
                                      ],
                          )

        create_efilter(constants.EFILTER_PARTICIPATE, name=_(u'In which I participate'),
                       model=Activity, is_custom=False, user='admin',
                       conditions=[EntityFilterCondition.build_4_relation_subfilter(
                                         rtype=rt_obj_part_2_activity,
                                         subfilter=EntityFilter.get_latest_version(FILTER_CONTACT_ME)
                                     ),
                                  ],
                      )

        # ---------------------------
        SearchConfigItem.create_if_needed(Activity, ['title', 'description', 'type__name'])

        # ---------------------------
        for user in get_user_model().objects.all():
            Calendar.get_user_default_calendar(user)

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.review_key.id,             defaults={'value': True})
        create_svalue(key_id=setting_keys.auto_subjects_key.id,      defaults={'value': True})
        create_svalue(key_id=setting_keys.form_user_messages_key.id, defaults={'value': False})

        # ---------------------------
        if not already_populated:
            LEFT = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            BlockDetailviewLocation.create_4_model_brick(order=5, zone=BlockDetailviewLocation.LEFT, model=Activity)

            create_bdl = BlockDetailviewLocation.create_if_needed
            create_bdl(brick_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=Activity)
            create_bdl(brick_id=bricks.RelatedCalendarBrick.id_,   order=90,  zone=LEFT,  model=Activity)
            create_bdl(brick_id=bricks.ParticipantsBrick.id_,      order=100, zone=LEFT,  model=Activity)
            create_bdl(brick_id=bricks.SubjectsBrick.id_,          order=120, zone=LEFT,  model=Activity)
            create_bdl(brick_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=Activity)
            create_bdl(brick_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=Activity)
            create_bdl(brick_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=Activity)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick_id=a_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=Activity)
                create_bdl(brick_id=a_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=Activity)
                create_bdl(brick_id=a_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=Activity)
                create_bdl(brick_id=a_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=Activity)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                create_bdl(brick_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=Activity)

            future_id = bricks.FutureActivitiesBrick.id_
            past_id   = bricks.PastActivitiesBrick.id_
            create_bdl(brick_id=future_id, order=20, zone=RIGHT, model=Contact)
            create_bdl(brick_id=past_id,   order=21, zone=RIGHT, model=Contact)
            create_bdl(brick_id=future_id, order=20, zone=RIGHT, model=Organisation)
            create_bdl(brick_id=past_id,   order=21, zone=RIGHT, model=Organisation)

            BlockPortalLocation.create_or_update(app_name='persons',    brick_id=future_id, order=20)
            BlockPortalLocation.create_or_update(app_name='persons',    brick_id=past_id,   order=21)

            BlockPortalLocation.create_or_update(app_name='creme_core', brick_id=future_id, order=20)
            BlockPortalLocation.create_or_update(app_name='creme_core', brick_id=past_id,   order=21)

            # ---------------------------
            create_button = ButtonMenuItem.create_if_needed
            create_button('activities-add_activity_button',  model=None, button=buttons.AddRelatedActivityButton, order=10)
            create_button('activities-add_meeting_button',   model=None, button=buttons.AddMeetingButton,         order=11)
            create_button('activities-add_phonecall_button', model=None, button=buttons.AddPhoneCallButton,       order=12)
            create_button('activities-add_task_button',      model=None, button=buttons.AddTaskButton,            order=13)
