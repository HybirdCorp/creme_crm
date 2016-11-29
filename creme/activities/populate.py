# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, ButtonMenuItem, SearchConfigItem,
        BlockDetailviewLocation, BlockPortalLocation, SettingValue,
        HeaderFilter, EntityFilter, EntityFilterCondition)
from creme.creme_core.utils import create_if_needed

from creme.persons.constants import FILTER_CONTACT_ME
from creme.persons import get_contact_model, get_organisation_model

from . import get_activity_model
from . import blocks, buttons, constants, setting_keys
from .models import ActivityType, ActivitySubType, Status, Calendar


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_LINKED_2_ACTIVITY).exists()

        Contact      = get_contact_model()
        Organisation = get_organisation_model()

        Activity = get_activity_model()

        # ---------------------------
        create_rtype = RelationType.create
        create_rtype((constants.REL_SUB_LINKED_2_ACTIVITY, _(u"related to the activity")),
                     (constants.REL_OBJ_LINKED_2_ACTIVITY, _(u"(activity) related to"),    [Activity])
                    )
        rt_obj_activity_subject = \
            create_rtype((constants.REL_SUB_ACTIVITY_SUBJECT, _(u"is subject of the activity"), [Contact, Organisation]),
                         (constants.REL_OBJ_ACTIVITY_SUBJECT, _(u'(activity) is to subject'),   [Activity])
                        )[1]
        rt_obj_part_2_activity = \
            create_rtype((constants.REL_SUB_PART_2_ACTIVITY, _(u"participates to the activity"),  [Contact]),
                         (constants.REL_OBJ_PART_2_ACTIVITY, _(u'(activity) has as participant'), [Activity]),
                         is_internal=True
                        )[1]

        # ---------------------------
        create_if_needed(Status, {'pk': constants.STATUS_PLANNED},     name=pgettext('activities-status', 'Planned'),     description=pgettext('activities-status', 'Planned'),     is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_IN_PROGRESS}, name=pgettext('activities-status', 'In progress'), description=pgettext('activities-status', 'In progress'), is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_DONE},        name=pgettext('activities-status', 'Done'),        description=pgettext('activities-status', 'Done'),        is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_DELAYED},     name=pgettext('activities-status', 'Delayed'),     description=pgettext('activities-status', 'Delayed'),     is_custom=False)
        create_if_needed(Status, {'pk': constants.STATUS_CANCELLED},   name=pgettext('activities-status', 'Cancelled'),   description=pgettext('activities-status', 'Cancelled'),   is_custom=False)

        # ---------------------------
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_TASK},      name=_(u"Task"),            default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        meeting_type = \
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_MEETING},   name=_(u"Meeting"),         default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        phone_call_type = \
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_PHONECALL}, name=_(u"Phone call"),      default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_GATHERING}, name=_(u"Gathering"),       default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_SHOW},      name=_(u"Show"),            default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_DEMO},      name=_(u"Demonstration"),   default_day_duration=0, default_hour_duration="01:00:00", is_custom=False)
        create_if_needed(ActivityType, {'pk': constants.ACTIVITYTYPE_INDISPO},   name=_(u"Indisponibility"), default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)

        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_MEETING},       name=_('Meeting'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION}, name=_('Qualification'),                      type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_REVIVAL},       name=_('Revival'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_NETWORK},       name=_('Network'),                            type=meeting_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_MEETING_OTHER},         name=pgettext('activities-meeting', 'Other'), type=meeting_type, is_custom=False)

        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING},   name=_('Incoming'),          type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING},   name=_('Outgoing'),          type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_CONFERENCE}, name=_('Conference'),        type=phone_call_type, is_custom=False)
        create_if_needed(ActivitySubType, {'pk': constants.ACTIVITYSUBTYPE_PHONECALL_FAILED},     name=_('Outgoing - Failed'), type=phone_call_type, is_custom=False)

        # ---------------------------
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_ACTIVITY, name=_(u'Activity view'), model=Activity,
                            cells_desc=[(EntityCellRegularField, {'name': 'start'}),
                                        (EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'type'}),
                                        EntityCellRelation(rtype=rt_obj_part_2_activity),
                                        EntityCellRelation(rtype=rt_obj_activity_subject),
                                        (EntityCellRegularField, {'name': 'user'}),
                                        (EntityCellRegularField, {'name': 'end'}),
                                       ]
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
        if not already_populated:
            LEFT = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Activity)

            create_bdl = BlockDetailviewLocation.create
            create_bdl(block_id=customfields_block.id_,            order=40,  zone=LEFT,  model=Activity)
            create_bdl(block_id=blocks.related_calendar_block.id_, order=90,  zone=LEFT,  model=Activity)
            create_bdl(block_id=blocks.participants_block.id_,     order=100, zone=LEFT,  model=Activity)
            create_bdl(block_id=blocks.subjects_block.id_,         order=120, zone=LEFT,  model=Activity)
            create_bdl(block_id=properties_block.id_,              order=450, zone=LEFT,  model=Activity)
            create_bdl(block_id=relations_block.id_,               order=500, zone=LEFT,  model=Activity)
            create_bdl(block_id=history_block.id_,                 order=20,  zone=RIGHT, model=Activity)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=Activity)
                create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=Activity)
                create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=Activity)
                create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=Activity)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.blocks import linked_docs_block

                create_bdl(block_id=linked_docs_block.id_, order=600, zone=RIGHT, model=Activity)

            future_id = blocks.future_activities_block.id_
            past_id   = blocks.past_activities_block.id_
            create_bdl(block_id=future_id, order=20, zone=RIGHT, model=Contact)
            create_bdl(block_id=past_id,   order=21, zone=RIGHT, model=Contact)
            create_bdl(block_id=future_id, order=20, zone=RIGHT, model=Organisation)
            create_bdl(block_id=past_id,   order=21, zone=RIGHT, model=Organisation)

            BlockPortalLocation.create(app_name='persons',    block_id=future_id, order=20)
            BlockPortalLocation.create(app_name='persons',    block_id=past_id,   order=21)

            BlockPortalLocation.create(app_name='creme_core', block_id=future_id, order=20)
            BlockPortalLocation.create(app_name='creme_core', block_id=past_id,   order=21)

            # ---------------------------
            create_button = ButtonMenuItem.create_if_needed
            create_button('activities-add_activity_button',  model=None, button=buttons.add_activity_button,  order=10)
            create_button('activities-add_meeting_button',   model=None, button=buttons.add_meeting_button,   order=11)
            create_button('activities-add_phonecall_button', model=None, button=buttons.add_phonecall_button, order=12)
            create_button('activities-add_task_button',      model=None, button=buttons.add_task_button,      order=13)

        # ---------------------------
        SearchConfigItem.create_if_needed(Activity, ['title', 'description', 'type__name'])

        # ---------------------------
        for user in get_user_model().objects.all():
            Calendar.get_user_default_calendar(user)

        # ---------------------------
        # create_svalue = SettingValue.create_if_needed
        # create_svalue(key=setting_keys.review_key,        user=None, value=True)
        # create_svalue(key=setting_keys.auto_subjects_key, user=None, value=True)
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.review_key.id,        defaults={'value': True})
        create_svalue(key_id=setting_keys.auto_subjects_key.id, defaults={'value': True})
