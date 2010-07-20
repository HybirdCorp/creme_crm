# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.gui.block import QuerysetBlock, list4url

from assistants.models import Action, Alert, Memo, ToDo


class TodosBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'todos')
    order_by      = '-creation_date'
    verbose_name  = _(u'Todos')
    template_name = 'assistants/block_todos.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, ToDo.get_todos(pk),
                                                            update_url='/assistants/todos/reload/%s/' % pk))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(context, ToDo.objects.filter(entity_content_type__id__in=ct_ids),
                                                            update_url='/assistants/todos/reload/portal/%s/' % list4url(ct_ids)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, ToDo.objects.all(),
                                                            update_url='/assistants/todos/reload/home/'))


class MemosBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'memos')
    order_by      = '-creation_date'
    verbose_name  = _(u'Mémos')
    template_name = 'assistants/block_memos.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, Memo.get_memos(pk),
                                                            update_url='/assistants/memos/reload/%s/' % pk))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(context, Memo.objects.filter(entity_content_type__id__in=ct_ids),
                                                            update_url='/assistants/memos/reload/portal/%s/' % list4url(ct_ids)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, Memo.objects.filter(on_homepage=True),
                                                            update_url='/assistants/memos/reload/home/'))


class AlertsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'alerts')
    order_by      = '-trigger_date'
    verbose_name  = _(u'Alertes')
    template_name = 'assistants/block_alerts.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, Alert.get_alerts(pk),
                                                            update_url='/assistants/alerts/reload/%s/' % pk))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(context, Alert.objects.filter(entity_content_type__id__in=ct_ids),
                                                            update_url='/assistants/alerts/reload/portal/%s/' % list4url(ct_ids)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, Alert.get_alerts(),
                                                            update_url='/assistants/alerts/reload/home/'))

class ActionsITBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_it')
    order_by      = 'deadline'
    verbose_name  = _(u'Actions dans les délais')
    template_name = 'assistants/block_actions_it.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context, Action.get_actions_it(context['today'], entity),
                                                            update_url='/assistants/actions/reload/%s/' % entity.pk))

    def portal_display(self, context, ct_ids):
        return self._render(self.get_block_template_context(context, Action.get_actions_it_for_cts(ct_ids, context['today']),
                                                            update_url='/assistants/actions/reload/portal/%s/' % list4url(ct_ids)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, Action.get_actions_it(context['today']),
                                                            update_url='/assistants/actions/reload/home/'))


class ActionsNITBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_nit')
    order_by      = 'deadline'
    verbose_name  = _(u'Réactions hors délais')
    template_name = 'assistants/block_actions_nit.html'

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context, Action.get_actions_nit(context['today'], entity),
                                                            update_url='/assistants/actions/reload/%s/' % entity.pk))

    def portal_display(self, context, ct_id):
        return self._render(self.get_block_template_context(context, Action.get_actions_nit_for_cts(ct_id, context['today']),
                                                            update_url='/assistants/actions/reload/portal/%s/' % list4url(ct_id)))

    def home_display(self, context):
        return self._render(self.get_block_template_context(context, Action.get_actions_nit(context['today']),
                                                            update_url='/assistants/actions/reload/home/'))


alerts_block      = AlertsBlock()
actions_it_block  = ActionsITBlock()
actions_nit_block = ActionsNITBlock()
memos_block       = MemosBlock()
todos_block       = TodosBlock()
