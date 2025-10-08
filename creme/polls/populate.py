################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2025  Hybird
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
from functools import partial

from django.apps import apps
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
from creme import persons, polls
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry, Separator1Entry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)

from . import bricks, constants, custom_forms, menu
from .models import PollType

logger = logging.getLogger(__name__)

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

PollCampaign = polls.get_pollcampaign_model()
PollForm     = polls.get_pollform_model()
PollReply    = polls.get_pollreply_model()

# UUIDs for instances which can be deleted
UUID_POLL_TYPE_SURVEY     = '90d3d792-4354-43d2-8da2-9abf7cdd1421'
UUID_POLL_TYPE_MONITORING = 'f3568c0a-ba44-485d-b4f3-88dac5c9477b'
UUID_POLL_TYPE_ASSESSMENT = '3b50033a-b77c-43e4-88ae-145e433dc1ca'


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_PFORM,
            model=PollForm,
            name=_('Form view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_PREPLY,
            model=PollReply,
            name=_('Reply view'),
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'pform'),
                (EntityCellRegularField, 'person'),
            ],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_PCAMPAIGN,
            model=PollCampaign,
            name=_('Campaign view'),
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'due_date'),
                (EntityCellRegularField, 'segment'),
            ],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.CAMPAIGN_CREATION_CFORM,
        custom_forms.CAMPAIGN_EDITION_CFORM,
        custom_forms.PFORM_CREATION_CFORM,
        custom_forms.PFORM_EDITION_CFORM,
    ]
    SEARCH = [
        SearchConfigItem.objects.builder(model=PollForm,     fields=['name']),
        SearchConfigItem.objects.builder(model=PollReply,    fields=['name']),
        SearchConfigItem.objects.builder(model=PollCampaign, fields=['name']),
    ]
    POLL_TYPES = [
        # is_custom=True => only created during the first execution
        PollType(uuid=UUID_POLL_TYPE_SURVEY,     name=_('Survey')),
        PollType(uuid=UUID_POLL_TYPE_MONITORING, name=_('Monitoring')),
        PollType(uuid=UUID_POLL_TYPE_ASSESSMENT, name=_('Assessment')),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.Contact      = persons.get_contact_model()
        # self.Organisation = persons.get_organisation_model()
        #
        # self.PollCampaign = polls.get_pollcampaign_model()
        # self.PollForm     = polls.get_pollform_model()
        # self.PollReply    = polls.get_pollreply_model()
        self.Contact      = Contact
        self.Organisation = Organisation

        self.PollCampaign = PollCampaign
        self.PollForm     = PollForm
        self.PollReply    = PollReply

    def _already_populated(self):
        return HeaderFilter.objects.filter(id=constants.DEFAULT_HFILTER_PFORM).exists()

    def _populate(self):
        super()._populate()
        self._populate_poll_types()

    def _populate_poll_types(self):
        self._save_minions(self.POLL_TYPES)

    # def _populate_header_filters(self):
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_PFORM,
    #         model=self.PollForm, name=_('Form view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_PREPLY,
    #         model=self.PollReply, name=_('Reply view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'pform'}),
    #             (EntityCellRegularField, {'name': 'person'}),
    #         ],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_PCAMPAIGN,
    #         model=self.PollCampaign, name=_('Campaign view'),
    #         cells_desc=[
    #             (EntityCellRegularField, {'name': 'name'}),
    #             (EntityCellRegularField, {'name': 'due_date'}),
    #             (EntityCellRegularField, {'name': 'segment'}),
    #         ],
    #     )

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.PollForm,     fields=['name'])
    #     create_sci(model=self.PollReply,    fields=['name'])
    #     create_sci(model=self.PollCampaign, fields=['name'])

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Tools')},
            role=None, superuser=False,
            defaults={'order': 100},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(
            entry_id=Separator1Entry.id,
            entry_data={'label': _('Polls')},
            order=300,
        )
        create_mitem(entry_id=menu.PollFormsEntry.id,     order=305)
        create_mitem(entry_id=menu.PollRepliesEntry.id,   order=310)
        create_mitem(entry_id=menu.PollCampaignsEntry.id, order=315)

    def _populate_bricks_config_for_pform(self):
        RIGHT = BrickDetailviewLocation.RIGHT
        TOP = BrickDetailviewLocation.TOP
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.PollForm, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': bricks.PollFormLinesBrick, 'order': 5, 'zone': TOP},

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': bricks.PollRepliesBrick,  'order':  5, 'zone': RIGHT},
                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_preply(self):
        RIGHT = BrickDetailviewLocation.RIGHT
        TOP = BrickDetailviewLocation.TOP
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.PollReply, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': bricks.PollReplyLinesBrick, 'order': 5, 'zone': TOP},

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_campaign(self):
        RIGHT = BrickDetailviewLocation.RIGHT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.PollCampaign, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': bricks.PollCampaignRepliesBrick, 'order':  5, 'zone': RIGHT},
                {'brick': core_bricks.HistoryBrick,        'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_persons(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'brick': bricks.PersonPollRepliesBrick,
                'order': 500, 'zone': BrickDetailviewLocation.RIGHT,
            },
            data=[{'model': self.Contact}, {'model': self.Organisation}],
        )

    def _populate_bricks_config_for_documents(self):
        # logger.info('Documents app is installed
        # => we use the documents block on detail views')

        from creme.documents.bricks import LinkedDocsBrick

        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'brick': LinkedDocsBrick, 'order': 600,
                'zone': BrickDetailviewLocation.RIGHT,
            },
            data=[
                {'model': m}
                for m in (self.PollForm, self.PollReply, self.PollCampaign)
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed'
            ' => we use the assistants blocks on detail view'
        )

        import creme.assistants.bricks as a_bricks

        for model in (self.PollForm, self.PollReply, self.PollCampaign):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model, 'zone': BrickDetailviewLocation.RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_pform()
        self._populate_bricks_config_for_preply()
        self._populate_bricks_config_for_campaign()

        self._populate_bricks_config_for_persons()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()
