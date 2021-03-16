# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import MenuConfigItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import PermissionsMixin
from creme.creme_core.views.generic.order import ReorderInstances

from ..forms import menu as menu_forms
from . import base


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/menu.html'


# TODO: 409 if ContainerEntry is not registered ?
class ContainerAdding(base.ConfigModelCreation):
    form_class = menu_forms.ContainerForm
    title = _('Add a container of entries')


class SpecialLevel0Adding(base.ConfigModelCreation):
    form_class = menu_forms.SpecialContainerAddingForm
    title = _('Add a special root entry')


class SpecialLevel1Adding(base.ConfigCreation):
    # form_class = MenuEntryForm
    # title = 'Add a special entry'
    submit_label = _('Add this entry')

    menu_registry = menu_registry
    entry_response_class = CremeJsonResponse
    entry_levels = [1]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry_class = None

    def form_valid(self, form):
        cdata = form.cleaned_data

        return self.entry_response_class(
            [
                {
                    'label': cdata.get('label'),
                    'value': {'id': self.kwargs['entry_id'], 'data': cdata},
                },
            ],
            safe=False,  # Result is not a dictionary
        )

    def get_entry_class(self):
        entry_cls = self.entry_class

        if entry_cls is None:
            entry_cls = self.menu_registry.get_class(self.kwargs['entry_id'])
            if entry_cls is None:
                raise Http404('Unknown entry type')

            if entry_cls.level not in self.entry_levels:
                raise Http404('Invalid entry type (bad level)')

            self.entry_class = entry_cls

        return entry_cls

    def get_form_class(self):
        return self.get_entry_class().form_class

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        if not form.fields:
            raise Http404('Invalid entry type (empty form)')

        return form

    def get_title(self):
        return self.get_entry_class().creation_label


class ContainerEdition(base.ConfigModelEdition):
    model = MenuConfigItem
    pk_url_kwarg = 'item_id'
    form_class = menu_forms.ContainerForm
    title = _('Edit the container «{object}»')

    def get_queryset(self):
        return super().get_queryset().filter(entry_id=ContainerEntry.id)


class Level0Deletion(base.ConfigDeletion):
    container_id_arg = 'id'

    menu_registry = menu_registry

    def perform_deletion(self, request):
        item_id = get_from_POST_or_404(
            request.POST, self.container_id_arg, cast=int,
        )

        item = get_object_or_404(MenuConfigItem, id=item_id)
        entries = self.menu_registry.get_entries([item])

        if not entries or entries[0].is_required:
            raise ConflictError('This is not a container which can be deleted')

        item.delete()


class Level0Reordering(PermissionsMixin, ReorderInstances):
    permissions = 'creme_core.can_admin'
    model = MenuConfigItem
    pk_url_kwarg = 'item_id'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model._default_manager.filter(parent=None)
