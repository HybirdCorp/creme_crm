################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

import warnings
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Model
from django.utils.formats import number_format
from django.utils.html import escape, format_html

from ..gui.view_tag import ViewTag
from ..utils.collections import InheritedDataChain
from ..utils.html import render_limited_list

if TYPE_CHECKING:
    from ..forms.listview import ListViewSearchField
    from ..gui.listview.search import AbstractListViewSearchFieldRegistry
    from .sorter import AbstractCellSorter


class FunctionFieldResult:
    __slots__ = ('_data',)

    # TODO: str_data => can be Any type (e.g. Decimal) ??
    def __init__(self, str_data: str):
        self._data: str = str_data

    def __str__(self):
        return self.render(ViewTag.HTML_DETAIL)

    def render(self, tag: ViewTag):
        return self._data if tag == ViewTag.TEXT_PLAIN else escape(self._data)


class FunctionFieldDecimal(FunctionFieldResult):
    def render(self, tag):
        return (
            number_format(self._data)
            if tag == ViewTag.TEXT_PLAIN else
            # TODO: escape() ?
            # TODO: "if self._data is not None else ''" ?
            number_format(self._data, force_grouping=True)
        )


class FunctionFieldLink(FunctionFieldResult):
    def __init__(self, label: str, url: str, is_deleted=False, help_text=''):
        super().__init__(label)
        self._url = url
        self._is_deleted = is_deleted
        self._help_text = help_text

    def render(self, tag):
        if tag == ViewTag.TEXT_PLAIN:
            return self._data

        help_text = self._help_text

        if tag == ViewTag.HTML_FORM:
            return format_html(
                '<a href="{url}" class="is_deleted" target="_blank"{extra_attr}>{label}</a>'
                if self._is_deleted else
                '<a href="{url}" target="_blank"{extra_attr}>{label}</a>',
                url=self._url,
                extra_attr=format_html(' title="{}"', help_text) if help_text else '',
                label=self._data,
            )

        return format_html(
            '<a href="{url}" class="is_deleted"{extra_attr}>{label}</a>'
            if self._is_deleted else
            '<a href="{url}"{extra_attr}>{label}</a>',
            url=self._url,
            extra_attr=format_html(' title="{}"', help_text) if help_text else '',
            label=self._data,
        )


class FunctionFieldColorAndLabel(FunctionFieldResult):
    def __init__(self, label: str, color: str):
        super().__init__(label)
        self._color = color

    def render(self, tag):
        if tag == ViewTag.TEXT_PLAIN:
            return self._data

        # tag == ViewTag.HTML_*:
        # TODO: factorise with FKPrinter.print_fk_colored_html()?
        return format_html(
            '<div class="ui-creme-colored_status">'
            ' <div class="ui-creme-color_indicator" style="background-color:#{color};"></div>'
            ' <span>{label}</span>'
            '</div>',
            color=self._color,
            label=self._data,
        )

# TODO: other types (date, datetime...)


class FunctionField:
    """A FunctionField is related to a model and represents a special method of
    this model : it has a verbose name and can be used by HeaderFilter to build
    a column (like regular fields).
    """
    name: str       = ''  # Name of the attr in the related model class
    verbose_name    = ''  # Verbose name (used by HeaderFilter)
    is_hidden: bool = False  # See EntityCell.is_hidden
    # TODO: what about FunctionFieldResultsList([FunctionFieldDecimal(...), ...])
    #         ==> FunctionFieldResultsList or FunctionFieldDecimal ??
    result_type: type[FunctionFieldResult] = FunctionFieldResult

    # Builder for the search-field (used to quick-search in list-views) ; in can be :
    #  - None (no quick-search for this FunctionField) (default value).
    #  - A class of field (should inherit <creme_core.forms.listview.ListViewSearchField>).
    #  - A class of field-registry
    #    (should inherit <creme_core.gui.listview.search.AbstractListViewSearchFieldRegistry>).
    search_field_builder: (
        None
        | type[ListViewSearchField]
        | type[AbstractListViewSearchFieldRegistry]
    ) = None

    # Class inheriting <creme_core.core.sorter.AbstractCellSorter>. Used to
    # order a QuerySet with the function field as sorting key.
    # <None> means no sorting.
    sorter_class: type[AbstractCellSorter] | None = None

    def __call__(self, entity, user):
        """"@return An instance of FunctionField object
        (so you can call render() on the result).
        """
        return self.result_type(getattr(entity, self.name)())

    def populate_entities(self, entities, user):
        """Optimisation used for list-views ; see HeaderFilter."""
        pass


class FunctionFieldResultsList(FunctionFieldResult):
    def __init__(self, iterable: Iterable[FunctionFieldResult]):
        self._data: list[FunctionFieldResult] = [*iterable]  # type: ignore

    def render(self, tag):
        # return (
        #     '/'.join(e.render(tag) for e in self._data)
        #     if tag == ViewTag.TEXT_PLAIN else
        #     format_html(
        #         '<ul>{}</ul>',
        #         format_html_join(
        #             '', '<li>{}</li>', ([e.render(tag)] for e in self._data)
        #         )
        #     )
        # )
        if tag == ViewTag.TEXT_PLAIN:
            return '/'.join(e.render(tag) for e in self._data)

        return render_limited_list(
            items=self._data,
            limit=settings.CELL_SIZE,
            render_item=lambda e: e.render(tag),
        )


# class _FunctionFieldRegistry:
class FunctionFieldRegistry:
    """Registry for FunctionFields.

    FunctionFields are registered relatively to a model.
    When retrieving the FunctionFields of a model, the FunctionFields of the
    parent models are returned too.
    For example, a model inheriting CremeEntity inherits the FunctionFields of CremeEntity.
    """

    class RegistrationError(Exception):
        pass

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self):
        self._func_fields_classes = InheritedDataChain(dict)

    def fields(self, model: type[Model]) -> Iterator[FunctionField]:
        """Generator which yield the instances of all the FunctionFields related to a model.

        @param model: A model class.
        @return: Instances of FunctionField.
        """
        all_fields = {
            ff_cls.name: ff_cls
            for model_ffields in self._func_fields_classes.chain(model)
            for ff_cls in model_ffields.values()
        }

        for ff_cls in all_fields.values():
            yield ff_cls()

    # TODO: accept instance too ?
    # TODO: 'default' argument ?
    def get(self, model: type[Model], name: str) -> FunctionField | None:
        """Get an instance of FunctionField related to a model, and by its name, if it exists.
        The function field if searched in the parent model too.

        @param model: A model class.
        @param name: Name (str) of the wanted FunctionField.
        @return: An instance of FunctionField, or <None> if not found.
        """
        for model_ffields in self._func_fields_classes.chain(model, parent_first=False):
            ff_cls = model_ffields.get(name)

            if ff_cls is not None:
                return ff_cls()

        return None

    def register(self,
                 model: type[Model],
                 *function_field_classes: type[FunctionField],
                 ) -> FunctionFieldRegistry:
        """Register some FunctionField classes related to a model.

        @param model: A model class.
        @param function_field_classes: Some classes inheriting FunctionField.
        @raise: RegistrationError if a name is duplicated.
        """
        setdefault = self._func_fields_classes[model].setdefault

        for ff_cls in function_field_classes:
            assert issubclass(ff_cls, FunctionField)

            if setdefault(ff_cls.name, ff_cls) is not ff_cls:
                raise self.RegistrationError(
                    f"Duplicated FunctionField's name: {ff_cls.name}"
                )

        return self

    # TODO: accept FunctionField names too ?
    def unregister(self,
                   model: type[Model],
                   *function_field_classes: type[FunctionField],
                   ) -> None:
        """Register some FunctionField classes related to a model.

        @param model: A model class.
        @param function_field_classes: Some classes inheriting FunctionField.
        @raise: UnRegistrationError if a FunctionField is not found.
        """
        model_ffields = self._func_fields_classes[model]

        for ff_cls in function_field_classes:
            if model_ffields.pop(ff_cls.name, None) is None:
                raise self.UnRegistrationError(
                    f'Invalid FunctionField "{ff_cls.name}" (already un-registered?)'
                )


# function_field_registry = _FunctionFieldRegistry()
function_field_registry = FunctionFieldRegistry()


def __getattr__(name):
    if name == '_FunctionFieldRegistry':
        warnings.warn(
            '"_FunctionFieldRegistry" is deprecated; use "FunctionFieldRegistry" instead.',
            DeprecationWarning,
        )
        return FunctionFieldRegistry

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
