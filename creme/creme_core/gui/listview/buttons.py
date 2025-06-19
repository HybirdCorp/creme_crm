################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2025  Hybird
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

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core import backends
from creme.creme_core.gui.mass_import import import_form_registry
from creme.creme_core.gui.visit import EntityVisitor
from creme.creme_core.models import CremeEntity, CustomEntityType
from creme.creme_core.utils.collections import FluentList
from creme.creme_core.utils.meta import Order

__all__ = (
    'ListViewButton',
    'BatchProcessButton',
    'CreationButton',
    'MassExportButton', 'MassExportHeaderButton', 'MassImportButton',
    'VisitorModeButton',
    'ListViewButtonList',
)


class ListViewButton:
    """Base class for the buttons displayed in list-views."""
    # Name/path of the template used to render the button.
    template_name: str = 'creme_core/listview/buttons/place-holder.html'
    context: dict[str, Any]

    def __init__(self, context: dict[str, Any] | None = None):
        """Constructor.

        @param context: A dictionary which should be passed to the template for
               its rendering (see <get_context()>).
               <None> (default value) means "empty dictionary".
        """
        self.context = context or {}

    def get_context(self, request, lv_context) -> dict[str, Any]:
        """ Get the specific part of the context of the template.
        This context should be inserted in the context with the key "button"
        (see the template-tag "creme_listview.listview_buttons")

        @param request: Current HTTPRequest object.
        @param lv_context: Template context of the related list-view.
        return: A dictionary.
        """
        return self.context


class CreationButton(ListViewButton):
    template_name = 'creme_core/listview/buttons/creation.html'

    def get_context(self, request, lv_context):
        context = super().get_context(request=request, lv_context=lv_context)

        model = self.get_model(lv_context=lv_context)
        context['label'] = self.get_label(request=request, model=model)
        context['url'] = self.get_url(request=request, model=model)
        context['is_allowed'] = self.is_allowed(request=request, model=model)

        return context

    def get_label(self, request, model: type[CremeEntity]) -> str:
        return model.creation_label

    def get_model(self, lv_context) -> type[CremeEntity]:
        return lv_context['model']

    def get_url(self, request, model: type[CremeEntity]) -> str:
        return model.get_create_absolute_url()

    def is_allowed(self, request, model: type[CremeEntity]) -> bool:
        return request.user.has_perm_to_create(model)


class MassExportButton(ListViewButton):
    template_name = 'creme_core/listview/buttons/mass-export.html'

    # TODO: try to extract it from the context ?
    export_backend_registry = backends.export_backend_registry

    def get_context(self, request, lv_context):
        context = super().get_context(request=request, lv_context=lv_context)
        context['backend_choices'] = [
            (backend.id, backend.verbose_name)
            for backend in self.export_backend_registry.backend_classes
        ]
        context['extra_q'] = lv_context['extra_q']

        return context


class MassExportHeaderButton(MassExportButton):
    template_name = 'creme_core/listview/buttons/mass-export-header.html'


class MassImportButton(ListViewButton):
    template_name = 'creme_core/listview/buttons/mass-import.html'

    import_backend_registry = backends.import_backend_registry
    import_form_registry = import_form_registry

    def get_context(self, request, lv_context):
        context = super().get_context(request=request, lv_context=lv_context)

        model = lv_context['model']
        context['show'] = (
            self.import_backend_registry and model in self.import_form_registry
        )
        # NB: better to inject ContentType than model class
        #     (template engine will not call it)
        context['content_type'] = ContentType.objects.get_for_model(model)

        return context


class BatchProcessButton(ListViewButton):
    template_name = 'creme_core/listview/buttons/batch-process.html'

    def get_context(self, request, lv_context):
        context = super().get_context(request=request, lv_context=lv_context)

        ce_type = CustomEntityType.objects.get_for_model(lv_context['model'])
        if ce_type and ce_type.deleted:
            context['error'] = _(
                'The batch processing is disabled because the custom type is deleted'
            )

        return context


class VisitorModeButton(ListViewButton):
    template_name = 'creme_core/listview/buttons/visitor-mode.html'

    def get_context(self, request, lv_context):
        context = super().get_context(request=request, lv_context=lv_context)
        visitor = None

        if lv_context['paginator'].count:
            state = lv_context['list_view_state']
            sort_order = Order.from_string(state.sort_order)  # TODO: <Order> in ListViewState?
            sort_cell_key = state.sort_cell_key
            extra_q = lv_context['extra_q']
            visitor = EntityVisitor(
                model=lv_context['model'],
                sort=f'{sort_order.prefix}{sort_cell_key}' if sort_cell_key else '',
                hfilter_id=state.header_filter_id,
                efilter_id=state.entity_filter_id,
                internal_q=extra_q['internal'] or '',
                requested_q=extra_q['requested'] or '',
                search_dict=state.search,
                callback_url=request.path,
            )

        context['visitor'] = visitor

        return context


class ListViewButtonList(FluentList):
    """List of classes inheriting ListViewButton."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = {}

    def update_context(self, **kwargs) -> ListViewButtonList:
        """Add information items in the context passed to the button instances."""
        self._context.update(**kwargs)
        return self

    @property
    def instances(self) -> Iterator[ListViewButton]:
        """Instantiate classes, passing them a copy of the context."""
        get_context = self._context.copy

        for button_class in self:
            yield button_class(get_context())
