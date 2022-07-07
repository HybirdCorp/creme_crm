# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import QuerysetBrick

from .models import History, WaitingAction
from .utils import is_sandbox_by_user


class CrudityQuerysetBrick(QuerysetBrick):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def detailview_display(self, context):
        if not context['user'].has_perm('crudity'):
            raise PermissionDenied(
                gettext(
                    'Error: you are not allowed to view this block: {}'
                ).format(self.id_)
            )


class BaseWaitingActionsBrick(CrudityQuerysetBrick):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend


class WaitingActionsBrick(BaseWaitingActionsBrick):
    # dependencies  = ()
    verbose_name  = _('Waiting actions')
    template_name = 'crudity/bricks/waiting-actions.html'
    order_by      = 'id'

    def __init__(self, backend):
        super().__init__(backend=backend)
        self.id_ = self.generate_id()

    def generate_id(self):
        return CrudityQuerysetBrick.generate_id(
            'crudity',
            f'waiting_actions-{self.backend.get_id()}',
        )

    def _iter_dependencies_info(self):
        yield 'crudity.waitingaction.' + self.backend.get_id()

    def detailview_display(self, context):
        # Credentials are OK: brick is not registered in brick registry,
        # so reloading is necessarily done with the custom view
        super().detailview_display(context)
        backend = self.backend
        ct = ContentType.objects.get_for_model(backend.model)

        waiting_actions = WaitingAction.objects.filter(
            ct=ct, source=backend.source, subject=backend.subject,
        )

        if is_sandbox_by_user:
            waiting_actions = waiting_actions.filter(user=context['user'])

        crud_input = backend.crud_input

        return self._render(self.get_template_context(
            context,
            waiting_actions,
            waiting_ct=ct,
            backend=backend,
            extra_header_actions=(
                action.render(backend=backend) for action in crud_input.brickheader_actions
            ) if crud_input else (),
        ))


class CrudityHistoryBrick(CrudityQuerysetBrick):
    # dependencies  = ()
    verbose_name  = _('History')
    template_name = 'crudity/bricks/history.html'
    order_by      = 'id'

    def __init__(self, ct):
        super().__init__()
        self.ct = ct
        self.id_ = self.generate_id()

    def generate_id(self):
        return f'block_crudity-{self.ct.id}'

    def detailview_display(self, context):
        # Credentials are OK: block is not registered in block registry,
        # so reloading is necessarily done with the custom view
        super().detailview_display(context)
        ct = self.ct

        histories = History.objects.filter(entity__entity_type=ct)
        # if self.is_sandbox_by_user:
        if is_sandbox_by_user:
            histories = histories.filter(user=context['user'])

        return self._render(self.get_template_context(context, histories, ct=ct))
