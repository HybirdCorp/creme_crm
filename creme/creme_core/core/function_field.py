# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.db.models.query_utils import Q
from django.utils.formats import number_format
from django.utils.html import escape, format_html, format_html_join

from ..utils.collections import InheritedDataChain


class FunctionFieldResult:
    __slots__ = ('_data',)

    def __init__(self, str_data):
        self._data = str_data

    # def __unicode__(self, str_data):
    def __str__(self):
        return self.for_html()

    def for_html(self):
        return escape(self._data)

    def for_csv(self):
        return self._data


class FunctionFieldDecimal(FunctionFieldResult):
    def _format_decimal(self):
        val = self._data
        # TODO: factorise with field_printers ?
        # TODO remove 'use_l10n' when settings.USE_L10N == True
        return number_format(val, use_l10n=True)  # TODO: ?? "if val is not None else ''"

    def for_html(self):
        return self._format_decimal()  # TODO: escape() ?

    def for_csv(self):
        return self._format_decimal()

# TODO: other types (date, datetime...)


class FunctionField:
    """A FunctionField is related to a model and represents a special method of
    this model : it has a verbose name and can be used by HeaderFilter to build
    a column (like regular fields).
    """
    name         = ''  # Name of the attr if the related model class
    verbose_name = ''  # Verbose name (used by HeaderFilter)
    has_filter   = False  # See EntityCell.has_a_filter
    is_hidden    = False  # See EntityCell.is_hidden
    choices      = None  # Choices for list_view filtering. Has to be like django choices (e.g: [(1, 'First choice', ...), ] )
    result_type  = FunctionFieldResult  # TODO: what about FunctionFieldResultsList([FunctionFieldDecimal(...), ...])
                                        #         ==> FunctionFieldResultsList or FunctionFieldDecimal ??

    @classmethod
    def filter_in_result(cls, search_string):
        return Q()

    def __call__(self, entity, user):
        """"@return An instance of FunctionField object
        (so you can call for_html()/for_csv() on the result).
        """
        return self.result_type(getattr(entity, self.name)())

    @classmethod
    def populate_entities(cls, entities, user):
        """Optimisation used for list-views ; see HeaderFilter"""
        pass


class FunctionFieldResultsList(FunctionFieldResult):
    def __init__(self, iterable):
        self._data = list(iterable)

    def for_html(self):
        return format_html('<ul>{}</ul>',
                           format_html_join(
                               '', '<li>{}</li>',
                               ([e.for_html()] for e in self._data)
                           )
                          )

    def for_csv(self):
        return '/'.join(e.for_csv() for e in self._data)


class FunctionFieldsManager:
    def __init__(self, *function_fields):
        warnings.warn('FunctionFieldsManager is deprecated ; '
                      'use the new method CremeAppConfig.register_function_fields() instead.',
                      DeprecationWarning,
                     )

        self._function_fields = {f_field.name: f_field for f_field in function_fields}
        self._parent = None

    def __iter__(self):
        manager = self

        while manager:
            for func_field in manager._function_fields.values():
                yield func_field

            manager = manager._parent

    def add(self, *function_fields):
        self._function_fields.update((f_field.name, f_field) for f_field in function_fields)

    def get(self, name):
        func_field = self._function_fields.get(name)

        if not func_field and self._parent:
            func_field = self._parent.get(name)

        return func_field

    def new(self, *function_fields):
        """Use this method when you inherit a class, and you want to add new
        function fields to the inherited class, but not to the base class.
        """
        ffm = FunctionFieldsManager(*function_fields)
        ffm._parent = self

        return ffm


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

    def fields(self, model):
        """Generator which yield the instances of all the FunctionFields related to a model.

        @param model: A model class.
        @return: Instances of FunctionField.
        """
        for ffields_dict in self._func_fields_classes.chain(model):
            for ff_cls in ffields_dict.values():
                yield ff_cls()

    # TODO: accept instance too ?
    # TODO: 'default' argument ?
    def get(self, model, name):
        """Get an instance of FunctionField related to a model, and by its name, if it exists.
        The function field if searched in the parent model too.

        @param model: A model class
        @param name: Name (str) of the wanted FunctionField.
        @return: An instance of FunctionField, or <None> if not found.
        """
        for model_ffields in self._func_fields_classes.chain(model, parent_first=False):
            ff_cls = model_ffields.get(name)

            if ff_cls is not None:
                return ff_cls()

    def register(self, model, *function_field_classes):
        """Register some FunctionField classes related to a model.

        @param model: A model class.
        @param function_field_classes: Some classes inheriting FunctionField.
        @raise: RegistrationError if a name is duplicated.
        """
        setdefault = self._func_fields_classes[model].setdefault

        for ff_cls in function_field_classes:
            assert issubclass(ff_cls, FunctionField)

            if setdefault(ff_cls.name, ff_cls) is not ff_cls:
                raise self.RegistrationError("Duplicated FunctionField's name: {}".format(ff_cls.name))

    # TODO: accept FunctionField names too ?
    def unregister(self, model, *function_field_classes):
        """Register some FunctionField classes related to a model.

        @param model: A model class.
        @param function_field_classes: Some classes inheriting FunctionField.
        @raise: RegistrationError if a FunctionField is not found.
        """
        model_ffields = self._func_fields_classes[model]

        for ff_cls in function_field_classes:
            if model_ffields.pop(ff_cls.name, None) is None:
                raise self.RegistrationError('This FunctionField is not registered '
                                             '(already un-registered ?): {}'.format(ff_cls.name)
                                             )


function_field_registry = _FunctionFieldRegistry()