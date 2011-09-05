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

from logging import info

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from creme_config.models.setting import SettingKey, SettingValue

from creme_core.models import *
from creme_core.utils import create_or_update as create
from creme_core.constants import *
from creme_core.blocks import properties_block, relations_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator


class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        create(Language, 1, name=_(u'French'),  code='FRA')
        create(Language, 2, name=_(u'English'), code='EN')

        create(Currency, DEFAULT_CURRENCY_PK,   name=_(u"Euro"),                    local_symbol=_(u"€"), international_symbol=_(u'EUR'), is_custom=False)
        create(Currency, 2,                     name=_(u"United States dollar"),    local_symbol=_(u"$"), international_symbol=_(u'USD'), is_custom=True)

        CremePropertyType.create(PROP_IS_MANAGED_BY_CREME, _(u'managed by Creme'))

        RelationType.create((REL_SUB_HAS, _(u'owns')),
                            (REL_OBJ_HAS, _(u'belongs to')))


        try:
            root = User.objects.get(pk=1)
        except User.DoesNotExist:
            login = password = 'root'

            root = User(pk=1, username=login, is_superuser=True)
            root.set_password(password)
            root.save()

            info('A super-user has been created with login="%(login)s" and password="%(password)s".' % {
                            'login':    login,
                            'password': password,
                        })

        sk = SettingKey.create(pk=SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
                               description=_(u"By default, are blocks open ?"),
                               app_label='creme_core', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk, user=None, value=True)

        sk2 = SettingKey.create(pk=SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS,
                                description=_(u"By default, are empty fields displayed ?"),
                                app_label='creme_core', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk2, user=None, value=True)

        sk3 = SettingKey.create(pk=DISPLAY_CURRENCY_LOCAL_SYMBOL,
                               description=_(u"Display the currency local symbol (ex: €) ? If no the international symbol will be used (ex: EUR)"),
                               app_label='creme_core', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk3, user=None, value=True)

        #BlockPortalLocation.create_empty_config() #default portal
        #BlockPortalLocation.create_empty_config('creme_core') #home
        BlockDetailviewLocation.create(block_id=properties_block.id_, order=450, zone=BlockDetailviewLocation.LEFT)
        BlockDetailviewLocation.create(block_id=relations_block.id_,  order=500, zone=BlockDetailviewLocation.LEFT)
        BlockDetailviewLocation.create(block_id=history_block.id_,    order=8,   zone=BlockDetailviewLocation.RIGHT)

        BlockPortalLocation.create(block_id=history_block.id_, order=8)
        BlockPortalLocation.create(block_id=history_block.id_, order=8, app_name='creme_core')

        BlockMypageLocation.create(block_id=history_block.id_, order=8)
        BlockMypageLocation.create(block_id=history_block.id_, order=8, user=root)

        if not ButtonMenuItem.objects.filter(content_type=None).exists():
            ButtonMenuItem.objects.create(pk='creme_core-void', content_type=None, button_id='', order=1)
