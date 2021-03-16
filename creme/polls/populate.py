# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
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

from creme import persons, polls
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
from creme.creme_core.utils import create_if_needed

from . import bricks, constants, custom_forms, menu
from .models import PollType

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self, *args, **kwargs):
        PollCampaign = polls.get_pollcampaign_model()
        PollForm     = polls.get_pollform_model()
        PollReply    = polls.get_pollreply_model()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_PFORM,
            model=PollForm, name=_('Form view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_PREPLY,
            model=PollReply, name=_('Reply view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'pform'}),
                (EntityCellRegularField, {'name': 'person'}),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_PCAMPAIGN,
            model=PollCampaign, name=_('Campaign view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'due_date'}),
                (EntityCellRegularField, {'name': 'segment'}),
            ],
        )

        # ---------------------------
        def build_custom_form_items(creation_descriptor, edition_descriptor, field_names):
            base_groups_desc = [
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
                }, {
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

            CustomFormConfigItem.objects.create_if_needed(
                descriptor=creation_descriptor,
                groups_desc=[
                    *base_groups_desc,
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
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=edition_descriptor,
                groups_desc=base_groups_desc,
            )

        build_custom_form_items(
            creation_descriptor=custom_forms.CAMPAIGN_CREATION_CFORM,
            edition_descriptor=custom_forms.CAMPAIGN_EDITION_CFORM,
            field_names=[
                'user',
                'name',
                'goal',
                'start',
                'due_date',
                'segment',
                'expected_count',
            ],
        )
        build_custom_form_items(
            creation_descriptor=custom_forms.PFORM_CREATION_CFORM,
            edition_descriptor=custom_forms.PFORM_EDITION_CFORM,
            field_names=['user', 'name', 'type'],
        )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(PollForm,     ['name'])
        create_searchconf(PollReply,    ['name'])
        create_searchconf(PollCampaign, ['name'])

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not PollType.objects.exists():
            create_if_needed(PollType, {'pk': 1}, name=_('Survey'))
            create_if_needed(PollType, {'pk': 2}, name=_('Monitoring'))
            create_if_needed(PollType, {'pk': 3}, name=_('Assessment'))

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='polls-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Tools')},
                defaults={'order': 100},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(
                entry_id=Separator1Entry.id,
                entry_data={'label': _('Polls')},
                order=300,
            )
            create_mitem(entry_id=menu.PollFormsEntry.id,     order=305)
            create_mitem(entry_id=menu.PollRepliesEntry.id,   order=310)
            create_mitem(entry_id=menu.PollCampaignsEntry.id, order=315)

        # ---------------------------
        # NB: no straightforward way to test that this populate script has not been already run
        if not BrickDetailviewLocation.objects.filter_for_model(PollForm).exists():
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': PollForm, 'zone': LEFT},
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
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': PollReply, 'zone': LEFT},
                data=[
                    {'brick': bricks.PollReplyLinesBrick, 'order': 5, 'zone': TOP},

                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': PollCampaign, 'zone': LEFT},
                data=[
                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order': 40},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': bricks.PollCampaignRepliesBrick, 'order': 5,  'zone': RIGHT},
                    {'brick': core_bricks.HistoryBrick,        'order': 20, 'zone': RIGHT},
                ],
            )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'brick': bricks.PersonPollRepliesBrick, 'order': 500, 'zone': RIGHT},
                data=[{'model': Contact}, {'model': Organisation}],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail view'
                )

                from creme.assistants import bricks as a_bricks

                for model in (PollForm, PollReply, PollCampaign):
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
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'brick': LinkedDocsBrick, 'order': 600, 'zone': RIGHT},
                    data=[{'model': m} for m in (PollForm, PollReply, PollCampaign)],
                )
