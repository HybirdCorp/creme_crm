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

from collections import defaultdict

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

#from creme_core.models import CremeEntity
from creme_core.gui.block import QuerysetBlock, list4url

from assistants.models import Action, Alert, Memo, ToDo, UserMessage


class _AssistantsBlock(QuerysetBlock):
    #configurable = True

    @staticmethod
    def _populate_related_real_entities(assistants, user):
        assistants = [assistant for assistant in assistants if assistant.entity_id]
        entities_ids_by_ct = defaultdict(set)

        for assistant in assistants:
            entities_ids_by_ct[assistant.entity_content_type_id].add(assistant.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for assistant in assistants:
            assistant.creme_entity = entities_map[assistant.entity_id]

        #CremeEntity.populate_credentials(entities_map.values(), user) #beware: values() and not itervalues()

    def _get_queryset_for_detailview(self, entity, context):
        """OVERLOAD ME"""
        pass

    def _get_queryset_for_home(self, context):
        """OVERLOAD ME"""
        pass

    def _get_queryset_for_portal(self, ct_ids, context):
        """OVERLOAD ME"""
        pass

    @classmethod
    def _get_contenttype_id(cls):
        return ContentType.objects.get_for_model(cls.dependencies[0]).id

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, self._get_queryset_for_detailview(entity, context),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                              ct_id=self._get_contenttype_id(),
                                             )

        #NB: optimisation ; it avoids the retrieving of the entity during template rendering.
        for assistant in btc['page'].object_list:
            assistant.creme_entity = entity

        return self._render(btc)

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context, self._get_queryset_for_portal(ct_ids, context),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                              ct_id=self._get_contenttype_id(),
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, self._get_queryset_for_home(context),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                              ct_id=self._get_contenttype_id(),
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class TodosBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'todos')
    dependencies  = (ToDo,)
    order_by      = '-creation_date'
    verbose_name  = _(u'Todos')
    template_name = 'assistants/block_todos.html'

    def _get_queryset_for_detailview(self, entity, context):
        return ToDo.get_todos(entity)

    def _get_queryset_for_home(self, context):
        return ToDo.get_todos_for_home(context['request'].user)

    def _get_queryset_for_portal(self, ct_ids, context):
        return ToDo.get_todos_for_ctypes(ct_ids, context['request'].user)


class MemosBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'memos')
    dependencies  = (Memo,)
    order_by      = '-creation_date'
    verbose_name  = _(u'Memos')
    template_name = 'assistants/block_memos.html'

    def _get_queryset_for_detailview(self, entity, context):
        return Memo.get_memos(entity)

    def _get_queryset_for_home(self, context):
        return Memo.get_memos_for_home(context['request'].user)

    def _get_queryset_for_portal(self, ct_ids, context):
        return Memo.get_memos_for_ctypes(ct_ids, context['request'].user)


class AlertsBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'alerts')
    dependencies  = (Alert,)
    order_by      = '-trigger_date'
    verbose_name  = _(u'Alerts')
    template_name = 'assistants/block_alerts.html'

    def _get_queryset_for_detailview(self, entity, context):
        return Alert.get_alerts(entity)

    def _get_queryset_for_home(self, context):
        return Alert.get_alerts_for_home(context['request'].user)

    def _get_queryset_for_portal(self, ct_ids, context):
        return Alert.get_alerts_for_ctypes(ct_ids, context['request'].user)


class ActionsITBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_it')
    dependencies  = (Action,)
    order_by      = 'deadline'
    verbose_name  = _(u'Actions in time')
    template_name = 'assistants/block_actions_it.html'

    def _get_queryset_for_detailview(self, entity, context):
        return Action.get_actions_it(entity, context['today'])

    def _get_queryset_for_home(self, context):
        return Action.get_actions_it_for_home(context['request'].user, context['today'])

    def _get_queryset_for_portal(self, ct_ids, context):
        return Action.get_actions_it_for_ctypes(ct_ids, context['request'].user, context['today'])


class ActionsNITBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'actions_nit')
    dependencies  = (Action,)
    order_by      = 'deadline'
    verbose_name  = _(u'Reactions not in time')
    template_name = 'assistants/block_actions_nit.html'

    def _get_queryset_for_detailview(self, entity, context):
        return Action.get_actions_nit(entity, context['today'])

    def _get_queryset_for_home(self, context):
        return  Action.get_actions_nit_for_home(context['request'].user, context['today'])

    def _get_queryset_for_portal(self, ct_ids, context):
        return Action.get_actions_nit_for_ctypes(ct_ids, context['request'].user, context['today'])


class UserMessagesBlock(_AssistantsBlock):
    id_           = QuerysetBlock.generate_id('assistants', 'messages')
    dependencies  = (UserMessage,)
    order_by      = '-creation_date'
    verbose_name  = _(u'User messages')
    template_name = 'assistants/block_messages.html'

    def _get_queryset_for_detailview(self, entity, context):
        return UserMessage.get_messages(entity, context['request'].user)

    def _get_queryset_for_home(self, context):
        return UserMessage.get_messages_for_home(context['request'].user)

    def _get_queryset_for_portal(self, ct_ids, context):
        return UserMessage.get_messages_for_ctypes(ct_ids, context['request'].user)


alerts_block      = AlertsBlock()
actions_it_block  = ActionsITBlock()
actions_nit_block = ActionsNITBlock()
memos_block       = MemosBlock()
todos_block       = TodosBlock()
messages_block    = UserMessagesBlock()
