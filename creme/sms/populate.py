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
from functools import partial

from django.apps import apps
from django.utils.translation import gettext as _

from creme import sms
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry, Separator1Entry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    HeaderFilter,
    MenuConfigItem,
    SearchConfigItem,
)

from . import bricks, constants, custom_forms, menu

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        SMSCampaign     = sms.get_smscampaign_model()
        MessagingList   = sms.get_messaginglist_model()
        MessageTemplate = sms.get_messagetemplate_model()

        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_MLIST,
            model=MessagingList,
            name=_('Messaging list view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_SMSCAMPAIGN,
            model=SMSCampaign,
            name=_('Campaign view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_MTEMPLATE,
            model=MessageTemplate,
            name=_('Message template view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        # ---------------------------
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

        def build_creation_custom_form_items(descriptor, field_names):
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=descriptor,
                groups_desc=[
                    {
                        'name': _('General information'),
                        'cells': [
                            *(
                                (EntityCellRegularField, {'name': fname})
                                for fname in field_names
                            ),
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                            ),
                        ],
                    },
                    *common_groups_desc,
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
                ],
            )

        def build_edition_custom_form_items(descriptor, field_names):
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=descriptor,
                groups_desc=[
                    {
                        'name': _('General information'),
                        'cells': [
                            *(
                                (EntityCellRegularField, {'name': fname})
                                for fname in field_names
                            ),
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                            ),
                        ],
                    },
                    *common_groups_desc,
                ],
            )

        build_creation_custom_form_items(
            descriptor=custom_forms.CAMPAIGN_CREATION_CFORM,
            field_names=['user', 'name', 'lists'],
        )
        build_edition_custom_form_items(
            descriptor=custom_forms.CAMPAIGN_EDITION_CFORM,
            field_names=['user', 'name'],  # 'lists'
        )

        templates_field_names = ['user', 'name', 'subject', 'body']
        build_creation_custom_form_items(
            descriptor=custom_forms.TEMPLATE_CREATION_CFORM,
            field_names=templates_field_names,
        )
        build_edition_custom_form_items(
            descriptor=custom_forms.TEMPLATE_EDITION_CFORM,
            field_names=templates_field_names,
        )

        mlist_field_names = ['user', 'name']
        build_creation_custom_form_items(
            descriptor=custom_forms.MESSAGINGLIST_CREATION_CFORM,
            field_names=mlist_field_names,
        )
        build_edition_custom_form_items(
            descriptor=custom_forms.MESSAGINGLIST_EDITION_CFORM,
            field_names=mlist_field_names,
        )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(SMSCampaign, ['name'])
        create_searchconf(MessagingList, ['name'])
        create_searchconf(MessageTemplate, ['name', 'subject', 'body'])

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='sms-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Marketing')},
                defaults={'order': 200},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(
                entry_id=Separator1Entry.id,
                entry_data={'label': _('SMS')},
                order=200,
            )
            create_mitem(entry_id=menu.SMSCampaignsEntry.id,     order=210)
            create_mitem(entry_id=menu.MessagingListsEntry.id,   order=215)
            create_mitem(entry_id=menu.MessageTemplatesEntry.id, order=220)

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(SMSCampaign).exists():
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': SMSCampaign, 'zone': LEFT},
                data=[
                    {'brick': bricks.SendingsBrick, 'order': 2,  'zone': TOP},

                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': bricks.MessagingListsBlock,    'order':  50},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': MessagingList, 'zone': LEFT},
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

                from creme.assistants import bricks as a_bricks

                for model in (SMSCampaign, MessagingList):
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
                    brick=LinkedDocsBrick, order=600, zone=RIGHT, model=SMSCampaign,
                )
