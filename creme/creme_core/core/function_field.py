# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
    Union,
)

from django.db.models import Model
from django.utils.formats import number_format
from django.utils.html import escape, format_html, format_html_join

from ..utils.collections import InheritedDataChain

if TYPE_CHECKING:
    from ..forms.listview import ListViewSearchField
    from ..gui.listview.search import AbstractListViewSearchFieldRegistry
    from .sorter import AbstractCellSorter


class FunctionFieldResult:
    __slots__ = ('_data',)

    # TODO: str_data => can be Any type (eg: Decimal) ??
    def __init__(self, str_data: str):
        self._data: str = str_data

    def __str__(self):
        return self.for_html()

    def for_html(self) -> str:
        return escape(self._data)

    def for_csv(self) -> str:
        return self._data


class FunctionFieldDecimal(FunctionFieldResult):
    def for_html(self) -> str:
        # TODO: escape() ?
        # TODO: remove 'use_l10n' when settings.USE_L10N == True
        # TODO: ?? "if self._data is not None else ''"
        return number_format(self._data, use_l10n=True, force_grouping=True)

    def for_csv(self) -> str:
        return number_format(self._data, use_l10n=True)


class FunctionFieldLink(FunctionFieldResult):
    def __init__(self, label: str, url: str, is_deleted=False):
        super().__init__(label)
        self._url = url
        self._is_deleted = is_deleted

    def for_html(self) -> str:
        return format_html(
            '<a href="{}" class="is_deleted">{}</a>'
            if self._is_deleted else
            '<a href="{}">{}</a>',
            self._url, self._data,
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
    result_type: Type[FunctionFieldResult] = FunctionFieldResult

    # Builder for the search-field (used to quick-search in list-views) ; in can be :
    #  - None (no quick-search for this FunctionField) (default value).
    #  - A class of field (should inherit <creme_core.forms.listview.ListViewSearchField>).
    #  - A class of field-registry
    #    (should inherit <creme_core.gui.listview.search.AbstractListViewSearchFieldRegistry>).
    search_field_builder: Union[
        None,
        Type['ListViewSearchField'],
        Type['AbstractListViewSearchFieldRegistry'],
    ] = None

    # Class inheriting <creme_core.core.sorter.AbstractCellSorter>. Used to
    # order a QuerySet with the function field as sorting key.
    # <None> means no sorting.
    sorter_class: Optional[Type['AbstractCellSorter']] = None

    def __call__(self, entity, user):
        """"@return An instance of FunctionField object
        (so you can call for_html()/for_csv() on the result).
        """
        return self.result_type(getattr(entity, self.name)())

    def populate_entities(self, entities, user):
        """Optimisation used for list-views ; see HeaderFilter."""
        pass


class FunctionFieldResultsList(FunctionFieldResult):
    def __init__(self, iterable: Iterable[FunctionFieldResult]):
        self._data: List[FunctionFieldResult] = [*iterable]  # type: ignore

    def for_html(self) -> str:
        return format_html(
            '<ul>{}</ul>',
            format_html_join(
                '', '<li>{}</li>',
                ([e.for_html()] for e in self._data)
            )
        )

    def for_csv(self) -> str:
        return '/'.join(e.for_csv() for e in self._data)


class _FunctionFieldRegistry:
    """Registry for FunctionFields.

    FunctionFields are registered relatively to a model.
    When retrieving the FunctionFields of a model, the FunctionFields of the
    parent models are returned too.
     eg: a model inheriting CremeEntity inherits the FunctionFields of CremeEntity.
    """

    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._func_fields_classes = InheritedDataChain(dict)

    def fields(self, model: Type[Model]) -> Iterator[FunctionField]:
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
    def get(self,
            model: Type[Model],
            name: str) -> Optional[FunctionField]:
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
                 model: Type[Model],
                 *function_field_classes: Type[FunctionField]) -> '_FunctionFieldRegistry':
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
                   model: Type[Model],
                   *function_field_classes: Type[FunctionField],
                   ) -> None:
        """Register some FunctionField classes related to a model.

        @param model: A model class.
        @param function_field_classes: Some classes inheriting FunctionField.
        @raise: RegistrationError if a FunctionField is not found.
        """
        model_ffields = self._func_fields_classes[model]

        for ff_cls in function_field_classes:
            if model_ffields.pop(ff_cls.name, None) is None:
                raise self.RegistrationError(
                    f'This FunctionField is not registered '
                    f'(already un-registered ?): {ff_cls.name}'
                )


function_field_registry = _FunctionFieldRegistry()
