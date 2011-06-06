# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from creme_config.models.setting import SettingKey, SettingValue

from creme_core.models import (RelationType, BlockConfigItem, CremePropertyType,
                               SearchConfigItem, ButtonMenuItem, HeaderFilterItem, HeaderFilter)
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Contact

from opportunities.models import Opportunity

from commercial.models import *
from commercial.blocks import approaches_block
from commercial.constants import *
from commercial.buttons import complete_goal_button


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_SOLD_BY,       _(u'has sold')),
                            (REL_OBJ_SOLD_BY,       _(u'has been sold by')))
        RelationType.create((REL_SUB_OPPORT_LINKED, _(u'is related to the commercial action'), [Opportunity]),
                            (REL_OBJ_OPPORT_LINKED, _(u'is related to the opportunity'),       [Act]))
        RelationType.create((REL_SUB_COMPLETE_GOAL, _(u'completes a goal of the commercial action')),
                            (REL_OBJ_COMPLETE_GOAL, _(u'is completed thanks to'),              [Act]))

        CremePropertyType.create(PROP_IS_A_SALESMAN, _(u'is a salesman'), [Contact])

        for i, title in enumerate((_('Phone calls'), _('Show'), _('Demo'))):
            create(ActType, i + 1, title=title, is_custom=False)

        create(BlockConfigItem, 'commercial-approaches_block', content_type=None, block_id=approaches_block.id_, order=10,  on_portal=False)

        hf = HeaderFilter.create(pk='commercial-hf_act', name=_(u"Com Action view"), model=Act)
        hf.set_items([HeaderFilterItem.build_4_field(model=Act, name='name'),
                      HeaderFilterItem.build_4_field(model=Act, name='expected_sales'),
                      HeaderFilterItem.build_4_field(model=Act, name='due_date'),
                     ])

        hf = HeaderFilter.create(pk='commercial-hf_strategy', name=_(u"Strategy view"), model=Strategy)
        hf.set_items([HeaderFilterItem.build_4_field(model=Strategy, name='name')])

        hf   = HeaderFilter.create(pk='commercial-hf_objpattern', name=_(u"Objective pattern view"), model=ActObjectivePattern)
        pref = 'commercial-hfi_objpattern_'
        hf.set_items([HeaderFilterItem.build_4_field(model=ActObjectivePattern, name='name'),
                      HeaderFilterItem.build_4_field(model=ActObjectivePattern, name='segment'),
                     ])

        ButtonMenuItem.create(pk='commercial-complete_goal_button', model=None, button=complete_goal_button, order=60)

        SearchConfigItem.create(Act, ['name', 'expected_sales', 'cost', 'goal'])
        SearchConfigItem.create(Strategy, ['name'])

        sk_com_app_email = SettingKey.create(pk=IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED,
                               description=_(u"Enable email reminder for commercial approaches"),
                               app_label='commercial', type=SettingKey.BOOL
                               )
        SettingValue.objects.create(key=sk_com_app_email, user=None, value=True)

        sk_com_app_only_orga = SettingKey.create(pk=DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW,
                               description=_(u"Display only organisations' commercial approaches on organisations' file. (Otherwise, display organisations', managers', employees', related opportunities' commercial approaches)"),
                               app_label='commercial', type=SettingKey.BOOL
                               )
        SettingValue.objects.create(key=sk_com_app_only_orga, user=None, value=True)
