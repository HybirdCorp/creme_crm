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

from decimal import Decimal
# import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _

from . import blocks, constants
from .creme_jobs import reminder_type
from .management.commands.creme_populate import BasePopulator
from .models import (RelationType, CremePropertyType, SettingValue, Currency, Language, Vat, Job,
        BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation, ButtonMenuItem)
from .setting_keys import block_opening_key, block_showempty_key, currency_symbol_key
from .utils import create_if_needed

# logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    def populate(self):
        already_populated = CremePropertyType.objects.filter(pk=constants.PROP_IS_MANAGED_BY_CREME).exists()

        CremePropertyType.create(constants.PROP_IS_MANAGED_BY_CREME, _(u'managed by Creme'))
        RelationType.create((constants.REL_SUB_HAS, _(u'owns')),
                            (constants.REL_OBJ_HAS, _(u'belongs to')))

        User = get_user_model()

        # TODO: if not already_populated  ??
        try:
            root = User.objects.get(pk=1)
        except User.DoesNotExist:
            login = password = 'root'

            root = User(pk=1, username=login, is_superuser=True,
                        first_name='Fulbert', last_name='Creme',
                       )
            root.set_password(password)
            root.save()

            if self.verbosity:
                self.stdout.write('\n A super-user has been created with login="%(login)s"'
                                  ' and password="%(password)s".' % {
                                        'login':    login,
                                        'password': password,
                                    },
                                  self.style.NOTICE,
                                 )
        else:
            # TODO: useless with django 1.8 ??
            if root.is_staff and User.objects.count() == 1:
                root.is_staff = False
                root.save()

        # ---------------------------
        # SettingValue.create_if_needed(key=block_opening_key,   user=None, value=True)
        # SettingValue.create_if_needed(key=block_showempty_key, user=None, value=True)
        # SettingValue.create_if_needed(key=currency_symbol_key, user=None, value=True)
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=block_opening_key.id,   defaults={'value': True})
        create_svalue(key_id=block_showempty_key.id, defaults={'value': True})
        create_svalue(key_id=currency_symbol_key.id, defaults={'value': True})

        # ---------------------------
        create_if_needed(Currency, {'pk': constants.DEFAULT_CURRENCY_PK}, name=_(u'Euro'), local_symbol=_(u'€'), international_symbol=_(u'EUR'), is_custom=False)

        # ---------------------------
        Job.objects.get_or_create(type_id=reminder_type.id,
                                  defaults={'language': settings.LANGUAGE_CODE,
                                            'status':   Job.STATUS_OK,
                                           },
                                 )

        if not already_populated:
            create_if_needed(Currency, {'pk': 2}, name=_(u'United States dollar'), local_symbol=_(u'$'), international_symbol=_(u'USD'))

            create_if_needed(Language, {'pk': 1}, name=_(u'French'),  code='FRA')
            create_if_needed(Language, {'pk': 2}, name=_(u'English'), code='EN')

            # ---------------------------
            LEFT = BlockDetailviewLocation.LEFT

            create_bdl = BlockDetailviewLocation.create
            BlockDetailviewLocation.create_4_model_block(order=5, zone=LEFT)
            create_bdl(block_id=blocks.customfields_block.id_, order=40,  zone=LEFT)
            create_bdl(block_id=blocks.properties_block.id_,   order=450, zone=LEFT)
            create_bdl(block_id=blocks.relations_block.id_,    order=500, zone=LEFT)
            create_bdl(block_id=blocks.history_block.id_,      order=8,   zone=BlockDetailviewLocation.RIGHT)

            BlockPortalLocation.create(block_id=blocks.history_block.id_, order=8)

            BlockPortalLocation.create(block_id=blocks.statistics_block.id_, order=8,  app_name='creme_core')
            BlockPortalLocation.create(block_id=blocks.history_block.id_,    order=10, app_name='creme_core')

            BlockMypageLocation.create(block_id=blocks.history_block.id_, order=8)
            BlockMypageLocation.create(block_id=blocks.history_block.id_, order=8, user=root)

            # ---------------------------
            if not ButtonMenuItem.objects.filter(content_type=None).exists():
                ButtonMenuItem.objects.create(pk='creme_core-void', content_type=None, button_id='', order=1)

            # ---------------------------
            values = {Decimal(value) for value in ['0.0', '5.50', '7.0', '19.60', '20.0', '21.20']}
            values.add(constants.DEFAULT_VAT)

            create_vat = Vat.objects.get_or_create
            for value in values:
                create_vat(value=value, is_default=(value == constants.DEFAULT_VAT), is_custom=False)

        if settings.TESTS_ON:
            from .tests import fake_populate
            fake_populate.populate()
