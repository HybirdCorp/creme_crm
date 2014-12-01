# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from decimal import Decimal
import logging

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from .blocks import properties_block, relations_block, customfields_block, history_block
from .constants import *
from .management.commands.creme_populate import BasePopulator
from .models import *
from .setting_keys import block_opening_key, block_showempty_key, currency_symbol_key
from .utils import create_if_needed

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    def populate(self):
        already_populated = CremePropertyType.objects.filter(pk=PROP_IS_MANAGED_BY_CREME).exists()


        CremePropertyType.create(PROP_IS_MANAGED_BY_CREME, _(u'managed by Creme'))


        RelationType.create((REL_SUB_HAS, _(u'owns')),
                            (REL_OBJ_HAS, _(u'belongs to')))


        #TODO: if not already_populated  ??
        try:
            root = User.objects.get(pk=1)
        except User.DoesNotExist:
            login = password = 'root'

            root = User(pk=1, username=login, is_superuser=True,
                        first_name='Fulbert', last_name='Creme',
                       )
            root.set_password(password)
            root.save()

            logger.info('A super-user has been created with login="%(login)s" and password="%(password)s".' % {
                            'login':    login,
                            'password': password,
                        })
        else:
            #User created by 'syncdb' is a staff user, which is annoying when there is only one user (he cannot own any entity)
            if root.is_staff and User.objects.count() == 1:
                root.is_staff = False
                root.save()


        SettingValue.create_if_needed(key=block_opening_key,   user=None, value=True)
        SettingValue.create_if_needed(key=block_showempty_key, user=None, value=True)
        SettingValue.create_if_needed(key=currency_symbol_key, user=None, value=True)


        create_if_needed(Currency, {'pk': DEFAULT_CURRENCY_PK}, name=_(u'Euro'), local_symbol=_(u'€'), international_symbol=_(u'EUR'), is_custom=False)


        if not already_populated:
            create_if_needed(Currency, {'pk': 2}, name=_(u'United States dollar'), local_symbol=_(u'$'), international_symbol=_(u'USD'))


            create_if_needed(Language, {'pk': 1}, name=_(u'French'),  code='FRA')
            create_if_needed(Language, {'pk': 2}, name=_(u'English'), code='EN')


            #BlockPortalLocation.create_empty_config() #default portal
            #BlockPortalLocation.create_empty_config('creme_core') #home
            BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT)
            BlockDetailviewLocation.create(block_id=customfields_block.id_, order=40,  zone=BlockDetailviewLocation.LEFT)
            BlockDetailviewLocation.create(block_id=properties_block.id_,   order=450, zone=BlockDetailviewLocation.LEFT)
            BlockDetailviewLocation.create(block_id=relations_block.id_,    order=500, zone=BlockDetailviewLocation.LEFT)
            BlockDetailviewLocation.create(block_id=history_block.id_,      order=8,   zone=BlockDetailviewLocation.RIGHT)

            BlockPortalLocation.create(block_id=history_block.id_, order=8)
            BlockPortalLocation.create(block_id=history_block.id_, order=8, app_name='creme_core')

            BlockMypageLocation.create(block_id=history_block.id_, order=8)
            BlockMypageLocation.create(block_id=history_block.id_, order=8, user=root)


            if not ButtonMenuItem.objects.filter(content_type=None).exists():
                ButtonMenuItem.objects.create(pk='creme_core-void', content_type=None, button_id='', order=1)


            #existing_vats = frozenset(Vat.objects.values_list('value', flat=True))
            #if not existing_vats:
            values = {Decimal(value) for value in ['0.0', '5.50', '7.0', '19.60', '20.0', '21.20']}
            values.add(DEFAULT_VAT)

            #create_vat = Vat.objects.create
            create_vat = Vat.objects.get_or_create
            for value in values:
                create_vat(value=value, is_default=(value == DEFAULT_VAT), is_custom=False)
