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

from django.conf import settings

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SettingValue, Job, BlockDetailviewLocation, BlockPortalLocation
from creme.creme_core.utils import create_if_needed

from .blocks import alerts_block, memos_block, todos_block, messages_block
from .constants import PRIO_IMP_PK, USERMESSAGE_PRIORITIES
from .creme_jobs import usermessages_send_type
from .models import UserMessagePriority
from .setting_keys import todo_reminder_key


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = UserMessagePriority.objects.filter(pk=PRIO_IMP_PK).exists()

        for pk, title in USERMESSAGE_PRIORITIES.iteritems():
            create_if_needed(UserMessagePriority, {'pk': pk}, title=unicode(title), is_custom=False)

        # SettingValue.create_if_needed(key=todo_reminder_key, user=None, value=9)
        SettingValue.objects.get_or_create(key_id=todo_reminder_key.id, defaults={'value': 9})

        Job.objects.get_or_create(type_id=usermessages_send_type.id,
                                  defaults={'language': settings.LANGUAGE_CODE,
                                            'status':   Job.STATUS_OK,
                                           },
                                 )

        if not already_populated:
            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT)

            BlockPortalLocation.create(block_id=memos_block.id_,    order=100)
            BlockPortalLocation.create(block_id=alerts_block.id_,   order=200)
            BlockPortalLocation.create(block_id=messages_block.id_, order=300)

            BlockPortalLocation.create(app_name='creme_core', block_id=memos_block.id_,    order=100)
            BlockPortalLocation.create(app_name='creme_core', block_id=alerts_block.id_,   order=200)
            BlockPortalLocation.create(app_name='creme_core', block_id=messages_block.id_, order=300)
