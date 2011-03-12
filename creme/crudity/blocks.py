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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock

from crudity.models import WaitingAction, History


class WaitingActionBlock(QuerysetBlock):
    dependencies  = ()
    verbose_name  = _(u'Waiting actions')
    template_name = 'crudity/templatetags/block_waiting_action.html'

    def __init__(self, ct, waiting_type):
        super(WaitingActionBlock, self).__init__()
        self.ct   = ct
        self.type = waiting_type
        self.id_  = self.generate_id()

    def generate_id(self):
        return 'block_crudity-%s-%s' % (self.ct.id, self.type)

    def detailview_display(self, context):
        #credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        type = self.type
        ct   = self.ct
        return self._render(self.get_block_template_context(context,
                                                            WaitingAction.objects.filter(ct=ct, type=type),
                                                            waiting_type=type,
                                                            waiting_ct=ct,
                                                            update_url='/crudity/waiting_actions_blocks/%s/reload' % (self.id_,),
                                                           ))


class HistoryBlock(QuerysetBlock):
    dependencies  = ()
    verbose_name  = _(u'History')
    template_name = 'crudity/templatetags/block_history.html'

    def __init__(self, ct, crud_type):
        super(HistoryBlock, self).__init__()
        self.ct   = ct
        self.type = crud_type
        self.id_  = self.generate_id()

    def generate_id(self):
        return 'block_crudity-%s-%s' % (self.ct.id, self.type)

    def detailview_display(self, context):
        #credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        type = self.type
        ct   = self.ct
        return self._render(self.get_block_template_context(context,
                                                            History.objects.filter(entity__entity_type=ct, type=type),
                                                            type=type,
                                                            ct=ct,
                                                            update_url='/crudity/history_block/%s/reload' % (self.id_,),
                                                           ))

