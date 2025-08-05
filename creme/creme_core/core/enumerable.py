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

from __future__ import annotations

import logging
# import warnings
from collections.abc import Iterable, Iterator, Sequence

# from django.conf import settings
from django.db.models import CharField, Field, Model
from django.db.models.query_utils import Q

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.collections import ClassKeyedMap

logger = logging.getLogger(__name__)


class Enumerator:
    """Class which can enumerate some choices (think <select> in HTML)."""
    field: Field

    def __init__(self, field: Field):
        """Constructor.

        @param field: Instance of model field (e.g. MyModel._meta.get_field('my_field')).
        """
        self.field = field

    def choices(self, user, *, term=None, only=None, limit=None) -> list[dict]:
        """Return the list of choices (see below) available for the given user.
        Abstract method.

        Each choice must be a dictionary, with the keys:
            value: Value of the choice (which will be POSTed). Mandatory.
            label: Label of the choice, displayed to the user. Mandatory.
            help:  Small additional description for the label. Optional.
            group: Group of the choice (think <optgroup> in HTML). Optional.

        @param user: Instance of User.
        @param term: Search words.
        @param only: List only choices with these values
        @return: List of choice-dictionaries.
        """
        raise NotImplementedError

    def to_python(self, user, values):
        """Return the list of the model instances related to the given values
        and available for the user.

        @param user: Instance of User.
        @param values: List of ids
        @return: List of model instances
        """
        raise NotImplementedError

    @classmethod
    def instance_as_dict(cls, instance) -> dict:
        return {
            'value': instance.pk,
            'label': str(instance),
        }

    @staticmethod
    def convert_choices(choices: Iterable[tuple]) -> Iterator[dict]:
        """Generators which converts Django-style choices into
        Enumerator-style choices.

        Django's style:
         - No-group: [(1, 'Foo'), (2, 'Bar'), (3, 'Baz')]
         - Group:    [('A',
                       [(1, 'Apple'), (2, 'Animal')]
                      ),
                      ('B',
                       [(3, 'Banana'), (4, 'Balloon')]
                      )
                    ]

         Enumerator's style: see choices().
        """
        for k0, v0 in choices:
            if isinstance(v0, list | tuple):
                for value, label in v0:
                    yield {'value': value, 'label': label, 'group': k0}
            else:
                yield {'value': k0, 'label': v0}


def get_enum_search_fields(field):
    search_fields = getattr(field.remote_field.model, '_search_fields', ())

    if not search_fields:
        remote_model_fields = field.remote_field.model._meta.get_fields()

        for search_field in remote_model_fields:
            if isinstance(search_field, CharField) and search_field.get_tag(FieldTag.VIEWABLE):
                search_fields = (search_field.get_attname_column()[1],)
                break

    return search_fields


class EmptyEnumerator(Enumerator):
    """Class which can enumerate nothing. Used as a placeholder if the enumerator
    cannot be found in the registry"""
    def choices(self, *args, **kwargs):
        # if settings.ENUMERABLE_REGISTRATION_ERROR:
        #     raise NotImplementedError(
        #         f'No enumerator has been found for the field "{self.field}". '
        #         'HINT: Register the field or its related model in apps config '
        #         '(see register_enumerable())'
        #     )
        # logger.error(
        #     'No enumerator has been found for the field "%s". '
        #     'Please register the field or its related model in apps config '
        #     '(see register_enumerable())', self.field
        # )
        # return ()
        raise NotImplementedError(
            f'No enumerator has been found for the field "{self.field}". '
            'HINT: Register the field or its related model in apps config '
            '(see register_enumerable())'
        )

    def to_python(self, user, values):
        return ()


class QSEnumerator(Enumerator):
    """Specialisation of Enumerator to enumerate elements of a QuerySet."""
    search_fields: Sequence[str] = ()
    limit_choices_to = None

    def __init__(self, field: Field, search_fields=None, limit_choices_to=None):
        super().__init__(field)

        search_fields = search_fields or self.search_fields
        limit_choices_to = limit_choices_to or self.limit_choices_to

        if not search_fields:
            search_fields = get_enum_search_fields(field)

        if not search_fields:
            raise ValueError(
                f'This field has no search fields : the model {field.model} of {field} do not'
                'have _search_fields attribute or visible CharField'
            )

        self.search_fields = search_fields
        self.limit_choices_to = limit_choices_to

    def search_q(self, term):
        q = Q()

        for name in self.search_fields:
            q |= Q(**{f'{name}__icontains': term})

        return q

    def _queryset(self, user):
        field = self.field
        qs = field.remote_field.model.objects.all()
        limit_choices_to = field.get_limit_choices_to()

        qs = qs.complex_filter(limit_choices_to) if limit_choices_to else qs
        qs = qs.complex_filter(self.limit_choices_to) if self.limit_choices_to else qs

        return qs

    def to_python(self, user, values):
        return list(self._queryset(user).filter(pk__in=values))

    def filter_term(self, queryset, term):
        return queryset.filter(self.search_q(term))

    def filter_only(self, queryset, values):
        return queryset.filter(id__in=values)

    def choices(self, user, *, term=None, only=None, limit=None):
        queryset = self._queryset(user)

        if term:
            queryset = self.filter_term(queryset, term)
        elif only:
            queryset = self.filter_only(queryset, only)

        return list(
            map(self.instance_as_dict, queryset[:limit] if limit else queryset)
        )


class EnumerableRegistry:
    """Registry which manages the choices available for (enumerable) model fields.

    E.g. will be used to propose available choices for filter-conditions
        related to a ForeignKey.

    The registry has a default behaviour for enumerable fields (it gets all the
    instances of the related instances -- using the attribute
    "limit_choices_too").
    The behaviour can be overridden for:
      - The model related to the ForeignKey/ManyToManyField (see register_related_model()).
      - The type (class) of the model-field which we want to enumerate (see register_field_type()).
      - The model-field which we want to enumerate (see register_field()).
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._enums_4_fields = {}
        self._enums_4_field_types = ClassKeyedMap()
        self._enums_4_models = {}

    def __str__(self):
        res = '_EnumerableRegistry:'

        if self._enums_4_fields:
            res += '\n  * Specific fields:'
            for field, enumerator_cls in self._enums_4_fields.items():
                res += '\n    - {field} -> {e_module}.{e_type}'.format(
                    field=field,
                    e_module=enumerator_cls.__module__,
                    e_type=enumerator_cls.__qualname__,
                )

        if self._enums_4_field_types:
            res += '\n  * Field types:'
            for field_type, enumerator_cls in self._enums_4_field_types.items():
                res += '\n    - {f_module}.{f_type} -> {e_cls}'.format(
                    f_module=field_type.__module__,
                    f_type=field_type.__name__,
                    e_cls=f'{enumerator_cls.__module__}.{enumerator_cls.__qualname__}'
                          if enumerator_cls else None,
                )

        if self._enums_4_models:
            res += '\n  * Related models:'
            for model, enumerator_cls in self._enums_4_models.items():
                res += '\n    - {app}.{model} -> {e_module}.{e_type}'.format(
                    app=model._meta.app_label,
                    model=model.__name__,
                    e_module=enumerator_cls.__module__,
                    e_type=enumerator_cls.__qualname__,
                )

        return res

    @staticmethod
    def _check_is_entity(model: type[Model]) -> None:
        # TODO: and registered as an entity ??
        if not issubclass(model, CremeEntity):
            raise ValueError(
                f'This model is not a CremeEntity: {model.__module__}.{model.__name__}'
            )

    @staticmethod
    def _check_viewable(field: Field) -> None:
        if not field.get_tag(FieldTag.VIEWABLE):
            raise ValueError(f'This field is not viewable: {field}')

    @staticmethod
    def _check_field(field: Field) -> None:
        # TODO: we probably should manage fields with is_relation==False but with
        #       a 'choices' attribute. Wait to add the feature in EntityFilterForm too.

        if not field.get_tag(FieldTag.ENUMERABLE):
            raise ValueError(f'This field is not enumerable: {field}')

    def _get_field(self, model: type[Model], field_name: str) -> Field:
        field = model._meta.get_field(field_name)  # Can raise FieldDoesNotExist
        self._check_field(field)

        return field

    def _enumerator(self, field: Field) -> Enumerator:
        enumerator_cls = (
            self._enums_4_fields.get(field)
            or self._enums_4_field_types[field.__class__]
            or self._enums_4_models.get(field.remote_field.model)
        )

        # Use QSEnumerator as default ONLY for a VIEWABLE CremeEntity field
        if enumerator_cls is None:
            self._check_viewable(field)
            self._check_is_entity(field.model)
            enumerator_cls = QSEnumerator

            # TODO: this is a hack because we cannot currently register 'EntityEnumerator'
            #       for all CremeEntity classes (see comment for 'register_related_model())
            if issubclass(field.remote_field.model, CremeEntity):
                from creme.creme_core.enumerators import EntityEnumerator
                enumerator_cls = EntityEnumerator

        return enumerator_cls(field)

    def enumerator_by_field(self, field: Field) -> Enumerator:
        """Get an Enumerator instance corresponding to a model field.

        @param field: Model field instance.
        @return: Instance of Enumerator.
        @raises: ValueError if the model or the field are invalid.
        """
        self._check_field(field)
        return self._enumerator(field)

    def enumerator_by_fieldname(self,
                                model: type[CremeEntity],
                                field_name: str,
                                ) -> Enumerator:
        """Get an Enumerator instance corresponding to a model field.

        @param model: Model inheriting CremeEntity.
        @param field_name: Name of a field (string).
        @return: Instance of Enumerator.
        @raises: ValueError if the model or the field are invalid.
        @raises: FieldDoesNotExist.
        """
        return self._enumerator(self._get_field(model, field_name))

    def register_field(self,
                       model: type[Model],
                       field_name: str,
                       enumerator_class: type[Enumerator],
                       ) -> EnumerableRegistry:
        """Customise the class of the enumerator returned by the methods
        enumerator_by_field[name] for a specific field.

        @param model: a django Model.
        @param field_name: Name of a field of <model>.
        @param enumerator_class: Class inheriting 'Enumerator'.
        @return: self (to chain calls to register_*() methods).
        @raises: ValueError if the model or the field are invalid.
        @raises: FieldDoesNotExist.
        """
        assert issubclass(enumerator_class, Enumerator)

        field = self._get_field(model, field_name)

        if self._enums_4_fields.setdefault(field, enumerator_class) is not enumerator_class:
            raise self.RegistrationError(
                f'{self.__class__.__name__}: this field is already registered: '
                f'{model.__name__}.{field_name}'
            )

        return self

    def register_field_type(self,
                            field_class: type[Field],
                            enumerator_class: type[Enumerator],
                            ) -> EnumerableRegistry:
        """Customise the class of the enumerator returned by the methods
        enumerator_by_field[name] for a specific field class.

        @param field_class: Class inheriting 'django.db.models.Field'.
        @param enumerator_class: Class inheriting 'Enumerator'.
        @return: self (to chain calls to register_*() methods).
        """
        assert issubclass(enumerator_class, Enumerator)

        self._enums_4_field_types[field_class] = enumerator_class

        return self

    # TODO: improve to register a base class, so all the child classes are using
    #       the enumerator class too (e.g. CremeEntity).
    def register_related_model(self,
                               model: type[Model],
                               enumerator_class: type[Enumerator],
                               ) -> EnumerableRegistry:
        """Customise the class of the enumerator returned by the methods
        enumerator_by_field[name] for ForeignKeys/ManyToManyFields
        which reference a specific model.

        @param model: Model (class inheriting 'django.db.models.Model').
        @param enumerator_class: Class inheriting 'Enumerator'.
        @return: self (to chain calls to register_*() methods).
        """
        assert issubclass(enumerator_class, Enumerator)

        if self._enums_4_models.setdefault(model, enumerator_class) is not enumerator_class:
            raise self.RegistrationError(
                f'{self.__class__.__name__}: this model is already registered: {model}'
            )

        return self


enumerable_registry = EnumerableRegistry()


# def __getattr__(name):
#     if name == '_EnumerableRegistry':
#         warnings.warn(
#             '"_EnumerableRegistry" is deprecated; use "EnumerableRegistry" instead.',
#             DeprecationWarning,
#         )
#         return EnumerableRegistry
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
