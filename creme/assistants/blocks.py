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

from collections import defaultdict

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity
from creme_core.gui.block import QuerysetBlock, list4url

from assistants.models import Action, Alert, Memo, ToDo


#TODO: factorise with a AssistantBlock ???

def _populate_related_real_entities(assistants, user):
    entities_ids_by_ct = defaultdict(set)

    for assistant in assistants:
        entities_ids_by_ct[assistant.entity_content_type_id].add(assistant.entity_id)

    entities_map = {}
    get_ct = ContentType.objects.get_for_id

    for ct_id, entities_ids in entities_ids_by_ct.iteritems():
        entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

    for assistant in assistants:
        assistant.creme_entity = entities_map[assistant.entity_id]

    CremeEntity.populate_credentials(entities_map.values(), user) #beware: values() and not itervalues()


class TodosBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'todos')
    dependencies  = (ToDo,)
    order_by      = '-creation_date'
    verbose_name  = _(u'Todos')
    template_name = 'assistants/block_todos.html'
    configurable  = True

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, ToDo.get_todos(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                             )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for todo in btc['page'].object_list:
            todo.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, ToDo.get_todos_for_ctypes(ct_ids),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, ToDo.get_todos(),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class MemosBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'memos')
    dependencies  = (Memo,)
    order_by      = '-creation_date'
    verbose_name  = _(u'Memos')
    template_name = 'assistants/block_memos.html'
    configurable  = True

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, Memo.get_memos(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                             )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for memo in btc['page'].object_list:
            memo.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, Memo.get_memos_for_ctypes(ct_ids),
                                                            update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                                            )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, Memo.get_home_memos(),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class AlertsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'alerts')
    dependencies  = (Alert,)
    order_by      = '-trigger_date'
    verbose_name  = _(u'Alerts')
    template_name = 'assistants/block_alerts.html'
    configurable  = True

    def detailview_display(self, context):
        entity = context['object']
        btc= self.get_block_template_context(context, Alert.get_alerts(entity),
                                             update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                            )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for alert in btc['page'].object_list:
            alert.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, Alert.get_alerts_for_ctypes(ct_ids),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, Alert.get_alerts(),
                                                            update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                                            )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class ActionsITBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_it')
    dependencies  = (Action,)
    order_by      = 'deadline'
    verbose_name  = _(u'Actions in time')
    template_name = 'assistants/block_actions_it.html'
    configurable  = True

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, Action.get_actions_it(context['today'], entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                             )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for action in btc['page'].object_list:
            action.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, Action.get_actions_it_for_ctypes(ct_ids, context['today']),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, Action.get_actions_it(context['today']),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class ActionsNITBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_nit')
    dependencies  = (Action,)
    order_by      = 'deadline'
    verbose_name  = _(u'Reactions not in time')
    template_name = 'assistants/block_actions_nit.html'
    configurable  = True

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, Action.get_actions_nit(context['today'], entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                             )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for action in btc['page'].object_list:
            action.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, Action.get_actions_nit_for_ctypes(ct_ids, context['today']),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, Action.get_actions_nit(context['today']),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        _populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


alerts_block      = AlertsBlock()
actions_it_block  = ActionsITBlock()
actions_nit_block = ActionsNITBlock()
memos_block       = MemosBlock()
todos_block       = TodosBlock()
