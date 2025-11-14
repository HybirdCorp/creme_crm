################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from creme import sms
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

logger = logging.getLogger(__name__)

SMSCampaign = sms.get_smscampaign_model()
MessagingList = sms.get_messaginglist_model()
MessageTemplate = sms.get_messagetemplate_model()


class Populator(BasePopulator):
    dependencies = ['creme_core']

    HEADER_FILTERS = [
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_MLIST,
            model=MessagingList,
            name=_('Messaging list view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_SMSCAMPAIGN,
            model=SMSCampaign,
            name=_('Campaign view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
        HeaderFilter.objects.proxy(
            id=constants.DEFAULT_HFILTER_MTEMPLATE,
            model=MessageTemplate,
            name=_('Message template view'),
            cells=[(EntityCellRegularField, 'name')],
        ),
    ]
    CUSTOM_FORMS = [
        custom_forms.CAMPAIGN_CREATION_CFORM,
        custom_forms.CAMPAIGN_EDITION_CFORM,
        custom_forms.TEMPLATE_CREATION_CFORM,
        custom_forms.TEMPLATE_EDITION_CFORM,
        custom_forms.MESSAGINGLIST_CREATION_CFORM,
        custom_forms.MESSAGINGLIST_EDITION_CFORM,
    ]
    SEARCH = [
        SearchConfigItem.objects.builder(model=SMSCampaign, fields=['name']),
        SearchConfigItem.objects.builder(model=MessagingList, fields=['name']),
        SearchConfigItem.objects.builder(
            model=MessageTemplate, fields=['name', 'subject', 'body'],
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.SMSCampaign     = sms.get_smscampaign_model()
        # self.MessagingList   = sms.get_messaginglist_model()
        # self.MessageTemplate = sms.get_messagetemplate_model()
        self.SMSCampaign     = SMSCampaign
        self.MessagingList   = MessagingList
        self.MessageTemplate = MessageTemplate

    def _already_populated(self):
        return HeaderFilter.objects.filter(id=constants.DEFAULT_HFILTER_MLIST).exists()

    # def _populate_header_filters(self):
    #     create_hf = HeaderFilter.objects.create_if_needed
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_MLIST,
    #         model=self.MessagingList,
    #         name=_('Messaging list view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_SMSCAMPAIGN,
    #         model=self.SMSCampaign,
    #         name=_('Campaign view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )
    #     create_hf(
    #         pk=constants.DEFAULT_HFILTER_MTEMPLATE,
    #         model=self.MessageTemplate,
    #         name=_('Message template view'),
    #         cells_desc=[(EntityCellRegularField, {'name': 'name'})],
    #     )

    # def _populate_search_config(self):
    #     create_sci = SearchConfigItem.objects.create_if_needed
    #     create_sci(model=self.SMSCampaign,     fields=['name'])
    #     create_sci(model=self.MessagingList,   fields=['name'])
    #     create_sci(model=self.MessageTemplate, fields=['name', 'subject', 'body'])

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Marketing')},
            role=None, superuser=False,
            defaults={'order': 200},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(
            entry_id=Separator1Entry.id,
            entry_data={'label': _('SMS')},
            order=200,
        )
        create_mitem(entry_id=menu.SMSCampaignsEntry.id,     order=210)
        create_mitem(entry_id=menu.MessagingListsEntry.id,   order=215)
        create_mitem(entry_id=menu.MessageTemplatesEntry.id, order=220)

    def _populate_bricks_config(self):
        TOP = BrickDetailviewLocation.TOP
        LEFT = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.SMSCampaign, 'zone': LEFT},
            data=[
                {'brick': bricks.SendingsBrick, 'order': 2, 'zone': TOP},

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.MessagingListsBrick,    'order':  50},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.MessagingList, 'zone': LEFT},
            data=[
                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.RecipientsBrick,        'order':  50},
                {'brick': bricks.ContactsBrick,          'order':  55},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

        if apps.is_installed('creme.assistants'):
            logger.info(
                'Assistants app is installed => we use the assistants blocks on detail views'
            )

            import creme.assistants.bricks as a_bricks

            for model in (self.SMSCampaign, self.MessagingList):
                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': model, 'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                    ],
                )

        if apps.is_installed('creme.documents'):
            # logger.info("Documents app is installed =>
            # we use the documents block on SMSCampaign's detail views")

            from creme.documents.bricks import LinkedDocsBrick

            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT, model=self.SMSCampaign,
            )
