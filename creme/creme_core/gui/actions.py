# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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
from django.db.models.base import Model
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.models.entity import CremeEntity
from creme.creme_core.templatetags.creme_ctype import ctype_can_be_merged
from creme.creme_core.utils.collections import InheritedDataChain


class ActionEntry:
    action_id = None
    action = ''
    action_url_name = None

    model = None

    label = ''
    icon = ''
    help_text = ''

    is_default = False
    is_visible = True
    is_enabled = True

    def __init__(self, user, model=None, instance=None, **kwargs):
        self.user = user
        self.instance = instance

        if model is None and instance is not None:
            model = instance.__class__

        if model is not None:
            self.model = model

        assert self.model is not None

        self.context = kwargs

    def _get_options(self):
        return None

    def _get_data(self):
        return None

    @classmethod
    def is_registered_for_bulk(cls, model, registry=None):
        registry = registry or actions_registry
        return registry.is_registered_for_bulk(model, cls)

    @classmethod
    def is_registered_for_instance(cls, model, registry=None):
        registry = registry or actions_registry
        return registry.is_registered_for_instance(model, cls)

    @property
    def ctype(self):
        return ContentType.objects.get_for_model(self.model)

    @property
    def action_data(self):
        options = self._get_options()
        data = self._get_data()
        action_data = None

        if options or data:
            action_data = {
                'options': options or {},
                'data': data or {}
            }

        return action_data

    @property
    def url(self):
        return reverse(self.action_url_name)


class EntityActionEntry(ActionEntry):
    model = CremeEntity


class EditActionEntry(EntityActionEntry):
    action_id = 'creme_core-edit'

    action = 'redirect'
    label = _('Edit')
    icon = 'edit'

    @property
    def url(self):
        return self.instance.get_edit_absolute_url()

    @property
    def is_enabled(self):
        return self.user.has_perm_to_change(self.instance)


class DeleteActionEntry(EntityActionEntry):
    action_id = 'creme_core-delete'

    action = 'delete'
    label = _('Delete')
    icon = 'delete'

    @property
    def url(self):
        return self.instance.get_delete_absolute_url()

    @property
    def is_enabled(self):
        return bool(self.url) and self.user.has_perm_to_delete(self.instance)


class ViewActionEntry(EntityActionEntry):
    action_id = 'creme_core-view'

    action = 'redirect'
    label = _('See')
    icon = 'view'

    is_default = True

    @property
    def url(self):
        return self.instance.get_absolute_url()

    @property
    def help_text(self):
        return gettext('Go to the entity {entity}').format(entity=self.instance)

    @property
    def is_enabled(self):
        return bool(self.url) and self.user.has_perm_to_view(self.instance)


class CloneActionEntry(EntityActionEntry):
    action_id = 'creme_core-clone'

    action = 'clone'
    label = _('Clone')
    icon = 'clone'

    @property
    def url(self):
        return self.instance.get_clone_absolute_url()

    def _get_data(self):
        return {
            'id': self.instance.id
        }

    @property
    def is_enabled(self):
        instance = self.instance
        user = self.user

        return (bool(self.url) and
                user.has_perm_to_create(instance) and
                user.has_perm_to_view(instance)
               )


class BulkEntityActionEntry(EntityActionEntry):
    bulk_max_count = None
    bulk_min_count = 1


class BulkEditActionEntry(BulkEntityActionEntry):
    action_id = 'creme_core-bulk_edit'

    action = 'edit-selection'
    action_url_name = 'creme_core__bulk_update'
    label = _('Multiple update')
    icon = 'edit'

    @property
    def url(self):
        return reverse(self.action_url_name, args=(self.ctype.id,))


class BulkDeleteActionEntry(BulkEntityActionEntry):
    action_id = 'creme_core-bulk_delete'

    action = 'delete-selection'
    action_url_name = 'creme_core__delete_entities'

    label=_('Multiple deletion')
    icon='delete'


class BulkAddPropertyActionEntry(BulkEntityActionEntry):
    action_id = 'creme_core-bulk_add_property'

    action = 'addto-selection'
    action_url_name = 'creme_core__add_properties_bulk'

    label=_('Multiple property adding')
    icon='property'

    @property
    def url(self):
        return reverse(self.action_url_name, args=(self.ctype.id,))


class BulkAddRelationActionEntry(BulkEntityActionEntry):
    action_id = 'creme_core-bulk_add_relation'

    action = 'addto-selection'
    action_url_name = 'creme_core__create_relations_bulk'

    label=_('Multiple relationship adding')
    icon='relations'

    @property
    def url(self):
        return reverse(self.action_url_name, args=(self.ctype.id,))


class MergeActionEntry(BulkEntityActionEntry):
    action_id = 'creme_core-merge'

    action = 'merge-selection'
    action_url_name = 'creme_core__merge_entities'

    label=_('Merge 2 entities')
    icon='merge'

    bulk_max_count = 2
    bulk_min_count = 2

    @property
    def is_enabled(self):
        return ctype_can_be_merged(self.ctype)

    @property
    def is_visible(self):
        return ctype_can_be_merged(self.ctype)


class ActionRegistrationError(Exception):
    pass


class VoidEntry:
    pass


class _ActionsRegistry:
    __slots__ = (
        '_instance_actions',
        '_bulk_actions'
    )

    def __init__(self):
        self._instance_actions = InheritedDataChain(dict)
        self._bulk_actions = InheritedDataChain(dict)

    def _inherited_actions(self, entries, model):
        result = {}

        for model_dict in entries.chain(model):
            result.update(model_dict)

        return result

    def _actions(self, entries, model):
        return [a  for a in self._inherited_actions(entries, model).values() if not issubclass(a, VoidEntry)]

    def _get_action(self, entries, action_id, model):
        for model_dict in entries.chain(model, parent_first=False):
            a = model_dict.get(action_id)

            if a is not None:
                return a if not issubclass(a, VoidEntry) else None

    def _validate_action(self, action):
        if not issubclass(action, ActionEntry):
            raise ActionRegistrationError("{} is not an ActionEntry".format(action))

        if getattr(action, 'model', None) is None:
            raise ActionRegistrationError("Invalid action {}. 'model' attribute must be defined".format(action))

        if not issubclass(action.model, Model):
            raise ActionRegistrationError("Invalid action {}. {} is not a Django Model".format(action, action.model))

        if getattr(action, 'action_id', None) is None:
            raise ActionRegistrationError("Invalid action {}. 'action_id' attribute must be defined".format(action))

        return action

    def _register_action(self, action, action_id, model, entries):
        registered = entries[model].setdefault(action_id, action)

        if registered is not action:
            if issubclass(action, VoidEntry):
                raise ActionRegistrationError("Unable to void action '{}'. An action is already defined for model {}".format(action_id, model))

            raise ActionRegistrationError("Duplicate action '{}' for model {}".format(action_id, model))

    def _register_actions(self, actions, entries):
        validate = self._validate_action
        register = self._register_action

        for action in actions:
            register(validate(action), action.action_id, action.model, entries)

    def _void_actions(self, model, actions, entries):
        register = self._register_action

        for action in actions:
            action_id = action if isinstance(action, str) else action.action_id
            register(VoidEntry, action_id, model, entries)

    def is_registered_for_instance(self, model, action):
        return self.instance_action(model, action.action_id) is not None

    def is_registered_for_bulk(self, model, action):
        return self.bulk_action(model, action.action_id) is not None

    def instance_action(self, model, action_id):
        return self._get_action(self._instance_actions, action_id, model)

    def bulk_action(self, model, action_id):
        return self._get_action(self._bulk_actions, action_id, model)

    def instance_actions(self, model):
        return self._actions(self._instance_actions, model)

    def bulk_actions(self, model):
        return self._actions(self._bulk_actions, model)

    def register_instance_actions(self, *actions):
        self._register_actions(actions, self._instance_actions)

    def register_bulk_actions(self, *actions):
        self._register_actions(actions, self._bulk_actions)

    def void_instance_actions(self, model, *actions):
        self._void_actions(model, actions, self._instance_actions)

    def void_bulk_actions(self, model, *actions):
        self._void_actions(model, actions, self._bulk_actions)


actions_registry = _ActionsRegistry()
