################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2025  Hybird
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

from django.core.exceptions import PermissionDenied
from django.urls.base import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .core.cloning import entity_cloner_registry
from .core.deletion import entity_deletor_registry
from .core.exceptions import ConflictError
from .gui.actions import BulkEntityAction, EntityAction
from .gui.merge import merge_form_registry


class EditAction(EntityAction):
    id = EntityAction.generate_id('creme_core', 'edit')

    type = 'redirect'
    label = _('Edit')
    icon = 'edit'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        self._url = url = instance.get_edit_absolute_url()
        self.is_visible = bool(url)

        try:
            self.user.has_perm_to_change_or_die(instance)
        except PermissionDenied as e:
            self.is_enabled = False
            self.help_text = str(e)

    @property
    def url(self):
        return self._url


class DeleteAction(EntityAction):
    id = EntityAction.generate_id('creme_core', 'delete')

    type = 'delete'
    label = _('Delete')
    icon = 'delete'

    deletor_registry = entity_deletor_registry

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        entity = self.instance
        deletor = self.deletor_registry.get(model=type(entity))
        if deletor is None:
            self.is_visible = False
        else:
            try:
                deletor.check_permissions(entity=entity, user=self.user)
            except (PermissionDenied, ConflictError) as e:
                self.is_enabled = False
                self.help_text = e.args[0]

    @property
    def url(self):
        return self.instance.get_delete_absolute_url()


class ViewAction(EntityAction):
    id = EntityAction.generate_id('creme_core', 'view')

    type = 'redirect'
    label = _('See')
    icon = 'view'

    is_default = True

    @property
    def url(self):
        return self.instance.get_absolute_url()

    @property
    def help_text(self):
        return gettext('Go to the entity {entity}').format(entity=self.instance)

    # TODO: can the url be empty?
    # @property
    # def is_enabled(self):
    #     return bool(self.url) and self.user.has_perm_to_view(self.instance)


class CloneAction(EntityAction):
    id = EntityAction.generate_id('creme_core', 'clone')

    type = 'clone'
    label = _('Clone')
    icon = 'clone'

    cloner_registry = entity_cloner_registry

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        entity = self.instance
        cloner = self.cloner_registry.get(model=type(entity))
        if cloner is None:
            self.is_visible = False
        else:
            try:
                cloner.check_permissions(entity=entity, user=self.user)
            except (PermissionDenied, ConflictError) as e:
                self.is_enabled = False
                self.help_text = e.args[0]

    @property
    def url(self):
        return self.instance.get_clone_absolute_url() if self.is_visible else ''

    def _get_data(self):
        return {
            'id': self.instance.id,
        }


class BulkEditAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('creme_core', 'bulk_edit')

    type = 'edit-selection'
    url_name = 'creme_core__bulk_update'
    label = _('Multiple update')
    icon = 'edit'

    @property
    def url(self):
        return reverse(self.url_name, args=(self.ctype.id,))


class BulkDeleteAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('creme_core', 'bulk_delete')

    type = 'delete-selection'
    url_name = 'creme_core__delete_entities'

    label = _('Multiple deletion')
    icon = 'delete'

    deletor_registry = entity_deletor_registry

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_visible = (self.deletor_registry.get(model=self.model) is not None)


class BulkAddPropertyAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('creme_core', 'bulk_add_property')

    type = 'addto-selection'
    url_name = 'creme_core__add_properties_bulk'

    label = _('Multiple property adding')
    icon = 'property'

    @property
    def url(self):
        return reverse(self.url_name, args=(self.ctype.id,))


class BulkAddRelationAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('creme_core', 'bulk_add_relation')

    type = 'addto-selection'
    url_name = 'creme_core__create_relations_bulk'

    label = _('Multiple relationship adding')
    icon = 'relations'

    @property
    def url(self):
        return reverse(self.url_name, args=(self.ctype.id,))


class MergeAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('creme_core', 'merge')

    type = 'merge-selection'
    url_name = 'creme_core__merge_entities'

    label = _('Merge 2 entities')
    icon = 'merge'

    bulk_max_count = 2
    bulk_min_count = 2

    merge_form_registry = merge_form_registry

    def _model_can_be_merged(self) -> bool:
        return self.model in self.merge_form_registry

    @property
    def is_enabled(self):
        return self._model_can_be_merged()

    @property
    def is_visible(self):
        return self._model_can_be_merged()
