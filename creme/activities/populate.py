################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

import creme.creme_core.bricks as core_bricks
from creme import persons
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
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
# from creme.creme_core.utils import create_if_needed
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
from .models import ActivitySubType, ActivityType, CalendarConfigItem, Status

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    BUTTONS = [
        # (class, order)
        (buttons.AddRelatedActivityButton, 10),
        (buttons.AddMeetingButton,         11),
        (buttons.AddPhoneCallButton,       12),
    ]
    SEARCH = ['title', 'description', 'type__name']
    STATUSES = [
        Status(
            uuid=constants.UUID_STATUS_PLANNED,
            name=pgettext('activities-status', 'Planned'),
            description=pgettext('activities-status', 'Planned'),
            is_custom=False,
        ),
        Status(
            uuid=constants.UUID_STATUS_IN_PROGRESS,
            name=pgettext('activities-status', 'In progress'),
            description=pgettext('activities-status', 'In progress'),
            is_custom=False,
        ),
        Status(
            uuid=constants.UUID_STATUS_DONE,
            name=pgettext('activities-status', 'Done'),
            description=pgettext('activities-status', 'Done'),
            is_custom=False,
        ),
        Status(
            uuid=constants.UUID_STATUS_DELAYED,
            name=pgettext('activities-status', 'Delayed'),
            description=pgettext('activities-status', 'Delayed'),
            is_custom=False,
        ),
        Status(
            uuid=constants.UUID_STATUS_CANCELLED,
            name=pgettext('activities-status', 'Cancelled'),
            description=pgettext('activities-status', 'Cancelled'),
            is_custom=False,
        ),
        Status(
            uuid=constants.UUID_STATUS_UNSUCCESSFUL,
            name=pgettext('activities-status', 'Unsuccessful'),
            description=_('Used by default by the button «Create an unsuccessful phone call»'),
            is_custom=False,
        ),
    ]
    ACTIVITY_TYPES = [
        [
            ActivityType(
                uuid=constants.UUID_TYPE_TASK,
                name=_('Task'),
                default_day_duration=0, default_hour_duration='00:15:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid='767b94e1-b366-4b97-8755-d719b268e402',
                    name=_('Task'), is_custom=True,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_MEETING,
                name=_('Meeting'),
                default_day_duration=0, default_hour_duration='00:15:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_MEETING_MEETING,
                    name=_('Meeting'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_MEETING_QUALIFICATION,
                    name=pgettext('activities-meeting', 'Qualification'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_MEETING_REVIVAL,
                    name=pgettext('activities-meeting', 'Revival'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_MEETING_NETWORK,
                    name=pgettext('activities-meeting', 'Network'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_MEETING_OTHER,
                    name=pgettext('activities-meeting', 'Other'), is_custom=False,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_PHONECALL,
                name=_('Phone call'),
                default_day_duration=0, default_hour_duration='00:15:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_PHONECALL_INCOMING,
                    name=pgettext('activities-phonecall', 'Incoming'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
                    name=pgettext('activities-phonecall', 'Outgoing'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
                    name=pgettext('activities-phonecall', 'Conference'), is_custom=False,
                ),
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_PHONECALL_FAILED,
                    name=pgettext('activities-phonecall', 'Outgoing - Failed'), is_custom=False,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_GATHERING,
                name=_('Gathering'),
                default_day_duration=0, default_hour_duration='00:15:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid='75b957a2-4fe7-4b98-8493-3f95e43a4968',
                    name=_('Gathering'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='2147569e-7bc4-4b79-8760-844dc568c422',
                    name=pgettext('activities-gathering', 'Team'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='e4ff08c8-80df-4528-bcc1-4f9d20c6fe61',
                    name=pgettext('activities-gathering', 'Internal'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='1c626935-d47a-4d9b-af4b-b90b8a71fc77',
                    name=_('On the site'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='8f003f06-f1ea-456e-90f3-82e8b8ef7424',
                    name=_('Remote'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='bc001a5c-eb90-4a3c-b703-afe347d3bf34',
                    name=_('Outside'), is_custom=True,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_SHOW,
                name=_('Show'),
                default_day_duration=1, default_hour_duration='00:00:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid='b75a663c-af2e-4440-89b3-2a75410cd55b',
                    name=_('Exhibitor'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='591b34b3-4226-48d4-a74d-d94665190b44',
                    name=_('Visitor'), is_custom=True,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_DEMO,
                name=_('Demonstration'),
                default_day_duration=0, default_hour_duration='01:00:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid='c32a94c7-8a2a-4589-8b0d-6764c63fb659',
                    name=_('Demonstration'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='247902ed-05dd-4ba6-9cbd-ea43b7c996eb',
                    name=_('On the site'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='e22a2e5d-4349-4d44-bd77-21b1a10816d5',
                    name=_('Outside'), is_custom=True,
                ),
                ActivitySubType(
                    uuid='3faf21bf-80b4-4182-b975-8146db2fb68b',
                    name=_('Videoconference'), is_custom=True,
                ),
            ]
        ], [
            ActivityType(
                uuid=constants.UUID_TYPE_UNAVAILABILITY,
                name=_('Unavailability'),
                default_day_duration=1, default_hour_duration='00:00:00',
                is_custom=False,
            ),
            [
                ActivitySubType(
                    uuid=constants.UUID_SUBTYPE_UNAVAILABILITY,
                    name=_('Unavailability'), is_custom=False,
                ),
                ActivitySubType(
                    uuid='d0408f78-77ba-4c49-9fa7-fc1e3455554e',
                    name=_('Holidays'), is_custom=True,

                ),
                ActivitySubType(
                    uuid='09baec7a-b0ba-4c03-8981-84fc066d2970',
                    name=_('Ill'), is_custom=True,
                ),
            ]
        ],
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()
        self.Activity = get_activity_model()

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_LINKED_2_ACTIVITY,
        ).exists()

    def _populate(self):
        self._populate_activity_types_and_sub_types()
        self._populate_status()
        self._populate_calendar_config()
        super()._populate()

    def _populate_status(self):
        # def create_status(pk, name):
        #     create_if_needed(
        #         Status,
        #         {'pk': pk},
        #         name=name, description=name, is_custom=False,
        #     )
        #
        # create_status(constants.STATUS_PLANNED,     pgettext('activities-status', 'Planned')),
        # create_status(constants.STATUS_IN_PROGRESS,
        #               pgettext('activities-status', 'In progress')),
        # create_status(constants.STATUS_DONE,        pgettext('activities-status', 'Done')),
        # create_status(constants.STATUS_DELAYED,     pgettext('activities-status', 'Delayed')),
        # create_status(constants.STATUS_CANCELLED,   pgettext('activities-status', 'Cancelled')),
        self._save_minions(self.STATUSES)

    def _populate_activity_types_and_sub_types(self):
        for atype, sub_types in self.ACTIVITY_TYPES:
            if atype.is_custom:
                continue

            try:
                atype = ActivityType.objects.get(uuid=atype.uuid)
            except ActivityType.DoesNotExist:
                atype.save()

                # The ActivityType did not exist, so we can create all subtypes
                for sub_type in sub_types:
                    sub_type.type = atype
                    sub_type.save()
            else:
                # The ActivityType already existed, so we only create missing mandatory subtypes
                for sub_type in sub_types:
                    if (
                        not sub_type.is_custom
                        and not ActivitySubType.objects.filter(uuid=sub_type.uuid).exists()
                    ):
                        sub_type.type = atype
                        sub_type.save()

        # NB: not useful in vanilla -- all types are is_custom==False
        #     (could be used by custom app to create types with is_custom==True)
        if not self.already_populated:
            for atype, sub_types in self.ACTIVITY_TYPES:
                if atype.is_custom:
                    atype.save()

                    for sub_type in sub_types:
                        sub_type.type = atype
                        sub_type.save()

    def _populate_calendar_config(self):
        # Create default calendar configuration
        CalendarConfigItem.objects.get_or_create(role=None, superuser=False)

    def _populate_relation_types(self):
        Contact = self.Contact
        Organisation = self.Organisation
        Activity = self.Activity

        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (
                constants.REL_SUB_LINKED_2_ACTIVITY,
                _('related to the activity'),
            ), (
                constants.REL_OBJ_LINKED_2_ACTIVITY,
                _('(activity) related to'),
                [Activity],
            ),
            minimal_display=(True, False),
        )
        create_rtype(
            (
                constants.REL_SUB_ACTIVITY_SUBJECT,
                _('is subject of the activity'),
                [Contact, Organisation],
            ), (
                constants.REL_OBJ_ACTIVITY_SUBJECT,
                _('(activity) has for subject'),
                [Activity],
            ),
            is_internal=True,  # NB: avoid the disabling of this RelationType
            minimal_display=(True, False),
        )
        create_rtype(
            (
                constants.REL_SUB_PART_2_ACTIVITY,
                _('participates in the activity'),
                [Contact],
            ), (
                constants.REL_OBJ_PART_2_ACTIVITY,
                _('(activity) has as participant'),
                [Activity],
            ),
            is_internal=True,
            minimal_display=(True, False),
        )

    def _populate_entity_filters(self):
        Activity = self.Activity
        create_efilter = EntityFilter.objects.smart_update_or_create

        # for pk, name, atype_id in [
        #     (constants.EFILTER_MEETINGS,   _('Meetings'),    constants.ACTIVITYTYPE_MEETING),
        #     (constants.EFILTER_PHONECALLS, _('Phone calls'), constants.ACTIVITYTYPE_PHONECALL),
        #     (constants.EFILTER_TASKS,      _('Tasks'),       constants.ACTIVITYTYPE_TASK),
        # ]:
        #     create_efilter(
        #         pk, name=name, model=Activity, is_custom=False, user='admin',
        #         conditions=[
        #             condition_handler.RegularFieldConditionHandler.build_condition(
        #                 model=Activity,
        #                 operator=operators.EqualsOperator,
        #                 field_name='type',
        #                 values=[atype_id],
        #             ),
        #         ],
        #     )
        for pk, name, atype_uuid in [
            (constants.EFILTER_MEETINGS,   _('Meetings'),    constants.UUID_TYPE_MEETING),
            (constants.EFILTER_PHONECALLS, _('Phone calls'), constants.UUID_TYPE_PHONECALL),
            (constants.EFILTER_TASKS,      _('Tasks'),       constants.UUID_TYPE_TASK),
        ]:
            create_efilter(
                pk, name=name, model=Activity, is_custom=False, user='admin',
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=Activity,
                        operator=operators.EqualsOperator,
                        field_name='type',
                        # values=[act_types[atype_uuid].id],
                        # NB: EntityFilterForm creates string in this case. So we use string:
                        #     - to be consistent
                        #     - to avoid the creation of new filters with version suffix "[2.6]"
                        values=[str(ActivityType.objects.get(uuid=atype_uuid).id)],
                    ),
                ],
            )

        create_efilter(
            constants.EFILTER_PARTICIPATE, name=_('In which I participate'),
            model=Activity, is_custom=False, user='admin',
            conditions=[
                condition_handler.RelationSubFilterConditionHandler.build_condition(
                    model=Activity,
                    # rtype=rt_obj_part_2_activity,
                    rtype=RelationType.objects.get(id=constants.REL_OBJ_PART_2_ACTIVITY),
                    subfilter=EntityFilter.objects.get_latest_version(FILTER_CONTACT_ME),
                ),
            ],
        )

    def _populate_header_filters(self):
        Activity = self.Activity
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_ACTIVITY,
            name=_('Activity view'),
            model=Activity,
            cells_desc=[
                (EntityCellRegularField, {'name': 'start'}),
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'type'}),
                EntityCellRelation(
                    model=Activity,
                    # rtype=rt_obj_part_2_activity,
                    rtype=RelationType.objects.get(id=constants.REL_OBJ_PART_2_ACTIVITY),
                ),
                EntityCellRelation(
                    model=Activity,
                    # rtype=rt_obj_activity_subject,
                    rtype=RelationType.objects.get(id=constants.REL_OBJ_ACTIVITY_SUBJECT),
                ),
                (EntityCellRegularField, {'name': 'user'}),
                (EntityCellRegularField, {'name': 'end'}),
            ],
        )

    def _populate_custom_forms(self):
        create_cfci = CustomFormConfigItem.objects.create_if_needed
        create_cfci(descriptor=custom_forms.ACTIVITY_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.ACTIVITY_CREATION_FROM_CALENDAR_CFORM)
        create_cfci(descriptor=custom_forms.UNAVAILABILITY_CREATION_CFORM)
        create_cfci(descriptor=custom_forms.ACTIVITY_EDITION_CFORM)

    def _populate_search_config(self):
        SearchConfigItem.objects.create_if_needed(
            model=self.Activity, fields=self.SEARCH,
        )

    def _populate_setting_values(self):
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.review_key.id,        defaults={'value': True})
        create_svalue(key_id=setting_keys.auto_subjects_key.id, defaults={'value': True})

        create_svalue(
            key_id=setting_keys.unsuccessful_subtype_key.id,
            defaults={'value': constants.UUID_SUBTYPE_PHONECALL_OUTGOING},
        )
        create_svalue(
            key_id=setting_keys.unsuccessful_title_key.id,
            defaults={'value': _('Unsuccessful call')},
        )
        create_svalue(
            key_id=setting_keys.unsuccessful_status_key.id,
            defaults={'value': constants.UUID_STATUS_UNSUCCESSFUL},
        )
        create_svalue(
            key_id=setting_keys.unsuccessful_duration_key.id,
            defaults={'value': 3},
        )

    def _populate_menu_config(self):
        create_mitem = MenuConfigItem.objects.create
        menu_container = create_mitem(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Activities')},
            order=10,
        )
        create_mitem(entry_id=menu.CalendarEntry.id,   order=10, parent=menu_container)
        create_mitem(entry_id=menu.ActivitiesEntry.id, order=20, parent=menu_container)
        create_mitem(entry_id=menu.PhoneCallsEntry.id, order=30, parent=menu_container)
        create_mitem(entry_id=menu.MeetingsEntry.id,   order=40, parent=menu_container)

    def _populate_buttons_config(self):
        create_bmi = ButtonMenuItem.objects.create_if_needed

        for button_cls, order in self.BUTTONS:
            create_bmi(button=button_cls, order=order)

    def _populate_bricks_config_for_activity(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Activity, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.RelatedCalendarBrick,   'order':  90},
                {'brick': bricks.ParticipantsBrick,      'order': 100},
                {'brick': bricks.SubjectsBrick,          'order': 120},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {
                    'brick': core_bricks.HistoryBrick,
                    'order': 20, 'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed'
            ' => we use the assistants blocks on detail views'
        )

        import creme.assistants.bricks as a_bricks

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Activity, 'zone': BrickDetailviewLocation.RIGHT},
            data=[
                {'brick': a_bricks.TodosBrick,        'order': 100},
                {'brick': a_bricks.MemosBrick,        'order': 200},
                {'brick': a_bricks.AlertsBrick,       'order': 300},
                {'brick': a_bricks.UserMessagesBrick, 'order': 400},
            ],
        )

    def _populate_bricks_config_for_documents(self):
        # logger.info('Documents app is installed
        # => we use the documents block on detail views')

        from creme.documents.bricks import LinkedDocsBrick

        BrickDetailviewLocation.objects.create_if_needed(
            brick=LinkedDocsBrick,
            order=600, zone=BrickDetailviewLocation.RIGHT,
            model=self.Activity,
        )

    def _populate_bricks_config_for_persons(self):
        future_id = bricks.FutureActivitiesBrick.id
        past_id = bricks.PastActivitiesBrick.id

        BrickDetailviewLocation.objects.multi_create(
            defaults={'zone': BrickDetailviewLocation.RIGHT},
            data=[
                {'brick': future_id, 'order': 20, 'model': self.Contact},
                {'brick': past_id,   'order': 21, 'model': self.Contact},
                {'brick': future_id, 'order': 20, 'model': self.Organisation},
                {'brick': past_id,   'order': 21, 'model': self.Organisation},
            ],
        )

    def _populate_bricks_config_for_home(self):
        create_bhl = BrickHomeLocation.objects.create
        create_bhl(brick_id=bricks.FutureActivitiesBrick.id, order=20)
        create_bhl(brick_id=bricks.PastActivitiesBrick.id,   order=21)

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_activity()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()

        self._populate_bricks_config_for_persons()
        self._populate_bricks_config_for_home()
