# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
# from django.conf import settings
# from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme import persons
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomFormConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
    SettingValue,
)
from creme.creme_core.utils import create_if_needed
from creme.persons.constants import FILTER_CONTACT_ME

from . import (
    bricks,
    buttons,
    constants,
    custom_forms,
    get_activity_model,
    menu,
    setting_keys,
)
# from .models import Calendar
from .forms import activity as act_forms
from .models import ActivitySubType, ActivityType, Status

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_LINKED_2_ACTIVITY,
        ).exists()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        Activity = get_activity_model()

        # ---------------------------
        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (constants.REL_SUB_LINKED_2_ACTIVITY, _('related to the activity')),
            (constants.REL_OBJ_LINKED_2_ACTIVITY, _('(activity) related to'),    [Activity]),
            minimal_display=(True, False),
        )
        rt_obj_activity_subject = create_rtype(
            (
                constants.REL_SUB_ACTIVITY_SUBJECT,
                _('is subject of the activity'),
                [Contact, Organisation],
            ), (
                constants.REL_OBJ_ACTIVITY_SUBJECT,
                _('(activity) has for subject'),
                [Activity],
            ),
            minimal_display=(True, False),
        )[1]
        rt_obj_part_2_activity = create_rtype(
            (constants.REL_SUB_PART_2_ACTIVITY, _('participates to the activity'),  [Contact]),
            (constants.REL_OBJ_PART_2_ACTIVITY, _('(activity) has as participant'), [Activity]),
            is_internal=True,
            minimal_display=(True, False),
        )[1]

        # ---------------------------
        def create_status(pk, name):
            create_if_needed(
                Status,
                {'pk': pk},
                name=name, description=name, is_custom=False,
            )

        create_status(constants.STATUS_PLANNED,     pgettext('activities-status', 'Planned')),
        create_status(constants.STATUS_IN_PROGRESS, pgettext('activities-status', 'In progress')),
        create_status(constants.STATUS_DONE,        pgettext('activities-status', 'Done')),
        create_status(constants.STATUS_DELAYED,     pgettext('activities-status', 'Delayed')),
        create_status(constants.STATUS_CANCELLED,   pgettext('activities-status', 'Cancelled')),

        # ---------------------------
        act_types_info = {
            constants.ACTIVITYTYPE_TASK: {
                'name': _('Task'),           'day': 0, 'hour': '00:15:00',
            },
            constants.ACTIVITYTYPE_MEETING: {
                'name': _('Meeting'),        'day': 0, 'hour': '00:15:00',
            },
            constants.ACTIVITYTYPE_PHONECALL: {
                'name': _('Phone call'),     'day': 0, 'hour': '00:15:00',
            },
            constants.ACTIVITYTYPE_GATHERING: {
                'name': _('Gathering'),      'day': 0, 'hour': '00:15:00',
            },
            constants.ACTIVITYTYPE_SHOW: {
                'name': _('Show'),           'day': 1, 'hour': '00:00:00',
            },
            constants.ACTIVITYTYPE_DEMO: {
                'name': _('Demonstration'),  'day': 0, 'hour': '01:00:00',
            },
            constants.ACTIVITYTYPE_INDISPO: {
                'name': _('Unavailability'), 'day': 1, 'hour': '00:00:00',
            },
        }
        act_types = {
            pk: create_if_needed(
                ActivityType,
                {'pk': pk},
                name=info['name'],
                default_day_duration=info['day'], default_hour_duration=info['hour'],
                is_custom=False,
            ) for pk, info in act_types_info.items()
        }

        def create_subtype(atype, pk, name):
            create_if_needed(
                ActivitySubType,
                {'pk': pk},
                name=name, type=atype, is_custom=False,
            )

        meeting_t = act_types[constants.ACTIVITYTYPE_MEETING]
        for pk, name in [
            (constants.ACTIVITYSUBTYPE_MEETING_MEETING,       _('Meeting')),
            (constants.ACTIVITYSUBTYPE_MEETING_QUALIFICATION, _('Qualification')),
            (constants.ACTIVITYSUBTYPE_MEETING_REVIVAL,       _('Revival')),
            (constants.ACTIVITYSUBTYPE_MEETING_NETWORK,       _('Network')),
            (constants.ACTIVITYSUBTYPE_MEETING_OTHER, pgettext('activities-meeting', 'Other')),
        ]:
            create_subtype(meeting_t, pk, name)

        pcall_t = act_types[constants.ACTIVITYTYPE_PHONECALL]
        for pk, name in [
            (constants.ACTIVITYSUBTYPE_PHONECALL_INCOMING,   _('Incoming')),
            (constants.ACTIVITYSUBTYPE_PHONECALL_OUTGOING,   _('Outgoing')),
            (constants.ACTIVITYSUBTYPE_PHONECALL_CONFERENCE, _('Conference')),
            (constants.ACTIVITYSUBTYPE_PHONECALL_FAILED,     _('Outgoing - Failed')),
        ]:
            create_subtype(pcall_t, pk, name)

        # ---------------------------
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_ACTIVITY,
            name=_('Activity view'),
            model=Activity,
            cells_desc=[
                (EntityCellRegularField, {'name': 'start'}),
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'type'}),
                EntityCellRelation(model=Activity, rtype=rt_obj_part_2_activity),
                EntityCellRelation(model=Activity, rtype=rt_obj_activity_subject),
                (EntityCellRegularField, {'name': 'user'}),
                (EntityCellRegularField, {'name': 'end'}),
            ],
        )

        # ---------------------------
        create_efilter = EntityFilter.objects.smart_update_or_create

        for pk, name, atype_id in [
            (constants.EFILTER_MEETINGS,   _('Meetings'),    constants.ACTIVITYTYPE_MEETING),
            (constants.EFILTER_PHONECALLS, _('Phone calls'), constants.ACTIVITYTYPE_PHONECALL),
            (constants.EFILTER_TASKS,      _('Tasks'),       constants.ACTIVITYTYPE_TASK),
        ]:
            create_efilter(
                pk, name=name, model=Activity, is_custom=False, user='admin',
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=Activity,
                        operator=operators.EqualsOperator,
                        field_name='type',
                        values=[atype_id],
                    ),
                ],
            )

        create_efilter(
            constants.EFILTER_PARTICIPATE, name=_('In which I participate'),
            model=Activity, is_custom=False, user='admin',
            conditions=[
                condition_handler.RelationSubFilterConditionHandler.build_condition(
                    model=Activity,
                    rtype=rt_obj_part_2_activity,
                    subfilter=EntityFilter.objects.get_latest_version(FILTER_CONTACT_ME),
                ),
            ],
        )

        # ---------------------------
        when_group = {
            'name': _('When'),
            'layout': LAYOUT_DUAL_SECOND,
            'cells': [
                act_forms.StartSubCell(model=Activity).into_cell(),
                act_forms.EndSubCell(model=Activity).into_cell(),
                (EntityCellRegularField, {'name': 'is_all_day'}),
            ],
        }
        alerts_groups = [
            {
                'name': _('Generate an alert on a specific date'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    act_forms.DatetimeAlertSubCell(model=Activity).into_cell(),
                ],
            }, {
                'name': _('Generate an alert in a while'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    act_forms.PeriodAlertSubCell(model=Activity).into_cell(),
                ],
            },
        ]
        participants_group = {
            'name': _('Participants & subjects'),
            'cells': [
                act_forms.MyParticipationSubCell(model=Activity).into_cell(),
                act_forms.ParticipatingUsersSubCell(model=Activity).into_cell(),
                act_forms.OtherParticipantsSubCell(model=Activity).into_cell(),
                act_forms.ActivitySubjectsSubCell(model=Activity).into_cell(),
                act_forms.LinkedEntitiesSubCell(model=Activity).into_cell(),
            ],
        }
        common_groups_desc = [
            {
                'name': _('Description'),
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]
        relations_n_properties_groups = [
            {
                'name': _('Properties'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                    ),
                ],
            }, {
                'name': _('Relationships'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.RELATIONS},
                    ),
                ],
            },
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.ACTIVITY_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'minutes'}),
                        (EntityCellRegularField, {'name': 'place'}),
                        (EntityCellRegularField, {'name': 'duration'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        (EntityCellRegularField, {'name': 'busy'}),
                        act_forms.ActivitySubTypeSubCell(model=Activity).into_cell(),
                        # act_forms.CommercialApproachSubCell(model=Activity).into_cell(),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                when_group,
                *alerts_groups,
                participants_group,
                *common_groups_desc,
                *relations_n_properties_groups,
                # {
                #     'name': _('Users to keep informed'),
                #     'cells': [
                #         (
                #             act_forms.UserMessagesSubCell(model=Activity).into_cell(),
                #         ),
                #     ],
                # },
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.ACTIVITY_CREATION_FROM_CALENDAR_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        # (EntityCellRegularField, {'name': 'minutes'}),
                        (EntityCellRegularField, {'name': 'place'}),
                        (EntityCellRegularField, {'name': 'duration'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        (EntityCellRegularField, {'name': 'busy'}),
                        act_forms.ActivitySubTypeSubCell(model=Activity).into_cell(),
                        # act_forms.CommercialApproachSubCell(model=Activity).into_cell(),
                        # NB: we do not want 'minutes' in the default form
                        # (
                        #     EntityCellCustomFormSpecial,
                        #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        # ),
                    ],
                },
                when_group,
                *alerts_groups,
                participants_group,
                *common_groups_desc,
                *relations_n_properties_groups,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.UNAVAILABILITY_CREATION_FROM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        act_forms.UnavailabilityTypeSubCell(model=Activity).into_cell(),
                    ],
                },
                when_group,
                {
                    'name': _('Unavailable users'),
                    'cells': [
                        act_forms.ParticipatingUsersSubCell(model=Activity).into_cell(),
                    ],
                },
                *common_groups_desc,
                *relations_n_properties_groups,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.ACTIVITY_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'minutes'}),
                        (EntityCellRegularField, {'name': 'place'}),
                        (EntityCellRegularField, {'name': 'duration'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        (EntityCellRegularField, {'name': 'busy'}),
                        act_forms.ActivitySubTypeSubCell(model=Activity).into_cell(),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                when_group,
                *common_groups_desc,
            ],
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(
            Activity, ['title', 'description', 'type__name'],
        )

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.review_key.id,        defaults={'value': True})
        create_svalue(key_id=setting_keys.auto_subjects_key.id, defaults={'value': True})
        # create_svalue(key_id=setting_keys.form_user_messages_key.id, defaults={'value': False})

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='activities-').exists():
            create_mitem = MenuConfigItem.objects.create
            container = create_mitem(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Activities')},
                order=10,
            )
            create_mitem(entry_id=menu.CalendarEntry.id,   order=10, parent=container)
            create_mitem(entry_id=menu.ActivitiesEntry.id, order=20, parent=container)
            create_mitem(entry_id=menu.PhoneCallsEntry.id, order=30, parent=container)
            create_mitem(entry_id=menu.MeetingsEntry.id,   order=40, parent=container)

        # ---------------------------
        if not already_populated:
            LEFT = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Activity, 'zone': LEFT},
                data=[
                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': bricks.RelatedCalendarBrick,   'order':  90},
                    {'brick': bricks.ParticipantsBrick,      'order': 100},
                    {'brick': bricks.SubjectsBrick,          'order': 120},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as a_bricks

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': Activity, 'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                    ],
                )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.create_if_needed(
                    brick=LinkedDocsBrick, order=600, zone=RIGHT, model=Activity,
                )

            future_id = bricks.FutureActivitiesBrick.id_
            past_id   = bricks.PastActivitiesBrick.id_

            BrickDetailviewLocation.objects.multi_create(
                defaults={'zone': RIGHT},
                data=[
                    {'brick': future_id, 'order': 20, 'model': Contact},
                    {'brick': past_id,   'order': 21, 'model': Contact},
                    {'brick': future_id, 'order': 20, 'model': Organisation},
                    {'brick': past_id,   'order': 21, 'model': Organisation},
                ],
            )

            BrickHomeLocation.objects.create(brick_id=future_id, order=20)
            BrickHomeLocation.objects.create(brick_id=past_id,   order=21)

            # ---------------------------
            create_button = ButtonMenuItem.objects.create_if_needed
            create_button(button=buttons.AddRelatedActivityButton, order=10)
            create_button(button=buttons.AddMeetingButton,         order=11)
            create_button(button=buttons.AddPhoneCallButton,       order=12)
