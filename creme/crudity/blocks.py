# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock

from creme_config.models import SettingValue

from emails.models import EntityEmail

from crudity.backends.models import CrudityBackend
from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.models import WaitingAction, History


class CrudityQuerysetBlock(QuerysetBlock):
    def __init__(self, *args, **kwargs):
        super(CrudityQuerysetBlock, self).__init__()

    def detailview_display(self, context):
        if not context['user'].has_perm('crudity'):
            raise PermissionDenied(_('Error: you are not allowed to view this block: %s' % self.id_))

    @property
    def is_sandbox_by_user(self):
        return SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None).value#No cache need sub-blocks are created on the fly


class WaitingActionBlock(CrudityQuerysetBlock):
    dependencies  = ()
    verbose_name  = _(u'Waiting actions')
    template_name = 'crudity/templatetags/block_waiting_action.html'

    def __init__(self, backend):
        super(WaitingActionBlock, self).__init__()
        self.backend = backend
        self.ct      = ContentType.objects.get_for_model(backend.model)
        self.id_     = self.generate_id()
        self.buttons = backend.get_rendered_buttons()

    def generate_id(self):
        return 'block_crudity-%s-%s' % (self.ct.id, CrudityBackend.normalize_subject(self.backend.subject))

    def detailview_display(self, context):
        #credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        super(WaitingActionBlock, self).detailview_display(context)
        ct   = self.ct
        backend = self.backend

        waiting_actions = WaitingAction.objects.filter(ct=ct, source=backend.source, subject=backend.subject)

        if self.is_sandbox_by_user:
            waiting_actions = waiting_actions.filter(user=context['user'])

        return self._render(self.get_block_template_context(context,
                                                            waiting_actions,
                                                            waiting_ct=ct,
                                                            email_ct=ContentType.objects.get_for_model(EntityEmail),#TODO: For now email, but generify this!
                                                            buttons=self.buttons,
                                                            backend=backend,
                                                            update_url='/crudity/waiting_actions_blocks/%s/reload' % (self.id_,),
                                                           ))


class HistoryBlock(CrudityQuerysetBlock):
    dependencies  = ()
    verbose_name  = _(u'History')
    template_name = 'crudity/templatetags/block_history.html'

    def __init__(self, ct, buttons=None):
        super(HistoryBlock, self).__init__()
        self.ct   = ct
        self.id_  = self.generate_id()
        self.buttons = buttons

    def generate_id(self):
        return 'block_crudity-%s' % (self.ct.id,)

    def detailview_display(self, context):
        #credentials are OK: block is not registered in block registry, so reloading is necessarily done with the custom view
        super(HistoryBlock, self).detailview_display(context)
        ct   = self.ct

        histories = History.objects.filter(entity__entity_type=ct)
        if self.is_sandbox_by_user:
            histories = histories.filter(user=context['user'])

        return self._render(self.get_block_template_context(context,
                                                            histories,
                                                            ct=ct,
                                                            buttons=self.buttons,
                                                            email_ct=ContentType.objects.get_for_model(EntityEmail),
                                                            update_url='/crudity/history_block/%s/reload' % (self.id_,),
                                                           ))

