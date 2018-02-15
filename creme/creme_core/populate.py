# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from . import bricks, constants, setting_keys
from .creme_jobs import reminder_type
from .management.commands.creme_populate import BasePopulator
from .models import (RelationType, SettingValue, Currency, Language, Vat, Job,
        BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation, ButtonMenuItem)  # CremePropertyType
from .utils import create_if_needed

# logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    def populate(self):
        already_populated = RelationType.objects.filter(id=constants.REL_SUB_HAS).exists()

        RelationType.create((constants.REL_SUB_HAS, _(u'owns')),
                            (constants.REL_OBJ_HAS, _(u'belongs to')))

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.block_opening_key.id,   defaults={'value': True})
        create_svalue(key_id=setting_keys.block_showempty_key.id, defaults={'value': True})
        create_svalue(key_id=setting_keys.currency_symbol_key.id, defaults={'value': True})

        # ---------------------------
        create_if_needed(Currency, {'pk': constants.DEFAULT_CURRENCY_PK}, name=_(u'Euro'), local_symbol=_(u'€'), international_symbol=_(u'EUR'), is_custom=False)

        # ---------------------------
        Job.objects.get_or_create(type_id=reminder_type.id,
                                  defaults={'language': settings.LANGUAGE_CODE,
                                            'status':   Job.STATUS_OK,
                                           },
                                 )

        if not already_populated:
            login = password = 'root'
            root = get_user_model().objects.create_superuser(pk=1, username=login, password=password,
                                                             first_name='Fulbert', last_name='Creme',
                                                             email=_(u'replaceMe@byYourAddress.com'),
                                                            )

            if self.verbosity:
                self.stdout.write('\n A super-user has been created with login="%(login)s"'
                                  ' and password="%(password)s".' % {
                                      'login':    login,
                                      'password': password,
                                  },
                                  self.style.NOTICE,
                                 )

            # ---------------------------
            create_if_needed(Currency, {'pk': 2}, name=_(u'United States dollar'), local_symbol=_(u'$'), international_symbol=_(u'USD'))

            create_if_needed(Language, {'pk': 1}, name=_(u'French'),  code='FRA')
            create_if_needed(Language, {'pk': 2}, name=_(u'English'), code='EN')

            # ---------------------------
            LEFT = BlockDetailviewLocation.LEFT

            create_bdl = BlockDetailviewLocation.create
            BlockDetailviewLocation.create_4_model_brick(order=5,        zone=LEFT)
            create_bdl(block_id=bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT)
            create_bdl(block_id=bricks.PropertiesBrick.id_,   order=450, zone=LEFT)
            create_bdl(block_id=bricks.RelationsBrick.id_,    order=500, zone=LEFT)
            create_bdl(block_id=bricks.HistoryBrick.id_,      order=8,   zone=BlockDetailviewLocation.RIGHT)

            BlockPortalLocation.create(block_id=bricks.HistoryBrick.id_, order=8)

            BlockPortalLocation.create(block_id=bricks.StatisticsBrick.id_, order=8,  app_name='creme_core')
            BlockPortalLocation.create(block_id=bricks.HistoryBrick.id_,    order=10, app_name='creme_core')

            BlockMypageLocation.create(block_id=bricks.HistoryBrick.id_, order=8)
            BlockMypageLocation.create(block_id=bricks.HistoryBrick.id_, order=8, user=root)

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
