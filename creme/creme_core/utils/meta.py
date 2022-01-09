# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2022 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from functools import partial
from itertools import chain
from typing import Callable, List, Optional, Tuple, Type, Union

from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db.models import DateField, Field, Model

from ..core.field_tags import FieldTag
from .unicode_collation import collator


class FieldInfo:
    """Class which stores a 'chain' of fields for a given model.

    Example:
        from django.db import models

        class Company(models.Model):
            name = models.CharField('Name', max_length=100)

        class Developer(models.Model):
            first_name = models.CharField('First name', max_length=100)
            last_name  = models.CharField('Last name', max_length=100)
            company    = models.ForeignKey(Company)

        class Software(models.Model):
            name     = models.CharField('Name', max_length=100)
            core_dev = models.ForeignKey(Developer)

        # Chain of 1 Field
        FieldInfo(Software, 'name')
        FieldInfo(Software, 'core_dev')

        # Chain of 2 Fields
        FieldInfo(Software, 'core_dev__name')
        FieldInfo(Software, 'core_dev__company')

        # Chain of 3 Fields
        FieldInfo(Software, 'core_dev__company__name')

    The string notation (like 'core_dev__company__name') is taken from django QuerySet ;
    so naturally the fields which can have "sub-fields" are fields like
    ForeignKeys or ManyToManyFields.
    """
    __slots__ = ('_model', '__fields')

    def __init__(self, model: Type[Model], field_name: str):
        """ Constructor.

        @param model: Class inheriting django.db.models.Model.
        @param field_name: String representing a 'chain' of fields; eg: 'book__author__name'.
        @throws FieldDoesNotExist
        """
        fields: List[Field] = []

        self.__fields = fields
        self._model: Type[Model] = model
        subfield_names = field_name.split('__')

        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            remote_field = getattr(field, 'remote_field', None)

            if remote_field is None:
                raise FieldDoesNotExist(
                    f'"{subfield_name}" is not a ForeignKey/ManyToManyField, '
                    f'so it can have a sub-field'
                )

            model = remote_field.model
            fields.append(field)

        fields.append(model._meta.get_field(subfield_names[-1]))

    def __getitem__(self, idx: Union[int, slice]):
        if isinstance(idx, slice):
            step = idx.step
            if step is not None and step != 1:
                raise ValueError('FieldInfo[] does not manage slice step.')

            # We avoid the call to __init__ and its introspection work
            fi = FieldInfo.__new__(FieldInfo)
            fi._model = self._model
            fi.__fields = new_fields = self.__fields[idx]

            if new_fields and idx.start:
                try:
                    fi._model = self.__fields[idx.start - 1].remote_field.model
                except IndexError:
                    pass

            return fi

        return self.__fields[idx]

    def __bool__(self):
        return bool(self.__fields)

    def __len__(self):
        return len(self.__fields)

    def __iter__(self):
        return iter(self.__fields)

    def __repr__(self):
        return 'FieldInfo(model={}, field_name="{}")'.format(
            self._model.__name__,
            '__'.join(f.name for f in self.__fields),
        )

    @property
    def model(self) -> Type[Model]:
        return self._model

    @property
    def verbose_name(self) -> str:
        return ' - '.join(str(field.verbose_name) for field in self.__fields)

    # TODO: probably does not work with several ManyToManyFields in the fields chain
    def value_from(self, instance: Model):
        if not isinstance(instance, self._model):
            raise ValueError(
                f'"{instance}" (type={type(instance)}) is not an instance of {self._model}'
            )

        result = instance

        for subfield in self:
            if result is None:
                break

            if isinstance(result, list):
                result = [getattr(elt, subfield.name) for elt in result]
            else:
                result = getattr(result, subfield.name)

                if subfield.many_to_many:
                    result = [*result.all()]

        return result


def is_date_field(field: Field) -> bool:
    return isinstance(field, DateField)


# ModelFieldEnumerator ---------------------------------------------------------

# Note
# #  - int argument is the depth in field chain (fk1__fk2__...)
# #  - returning <True> means "the field is accepted".
# FieldFilterFunctionType = Callable[[Field, int], bool]
# Notes:
#  - Arguments: they are passed with keywords only (Callable is not made to indicate that...)
#    - "model": the 'django.db.models.Model' class owning the field
#    - "field": instance of 'django.db.models.Field' wre are filtering.
#    - "depth": int indicating the depth in field chain (fk1__fk2__...)
#  - Return value: <True> means "the field is accepted".
FieldFilterFunctionType = Callable[[Type[Model], Field, int], bool]


class _FilterModelFieldQuery:
    # _TAGS = ('viewable', 'clonable', 'enumerable', 'optional')

    def __init__(self, function: Optional[FieldFilterFunctionType] = None, **kwargs):
        conditions: List[FieldFilterFunctionType] = []

        if function:
            conditions.append(function)

        for attr_name, value in kwargs.items():
            fun = (
                # (lambda field, deep, attr_name, value: field.get_tag(attr_name) == value)
                (
                    lambda *, model, field, depth, attr_name, value:
                    field.get_tag(attr_name) == value
                )
                # if attr_name in self._TAGS else
                if FieldTag.is_valid(attr_name) else
                # (lambda field, deep, attr_name, value: getattr(field, attr_name) == value)
                (
                    lambda *, model, field, depth, attr_name, value:
                    getattr(field, attr_name) == value
                )
            )

            conditions.append(partial(fun, attr_name=attr_name, value=value))

        self._conditions = conditions

    # def __call__(self, field, deep):
    def __call__(self, *, model, field, depth):
        # return all(cond(field, deep) for cond in self._conditions)
        # NB: the argument "model" is important because with inheritance it can
        #     be different than "field.model"
        return all(
            cond(model=model, field=field, depth=depth) for cond in self._conditions
        )


class _ExcludeModelFieldQuery(_FilterModelFieldQuery):
    # def __call__(self, field, deep):
    def __call__(self, *, model, field, depth):
        # return not any(cond(field, deep) for cond in self._conditions)
        return not any(
            cond(model=model, field=field, depth=depth) for cond in self._conditions
        )


class ModelFieldEnumerator:
    def __init__(self,
                 model: Type[Model],
                 # deep: int = 0,
                 depth: int = 0,
                 # only_leafs: bool = True):
                 only_leaves: bool = True,
                 ):
        """Constructor.
        @param model: DjangoModel class.
        @param depth: Depth of the returned fields (0=fields of the class, 1=also
               the fields of directly related classes, etc...).
        @param only_leaves: If True, FK/M2M fields are not returned (but eventually,
               their sub-fields, depending of the 'depth' parameter of course).
        """
        self._model = model
        # self._deep = deep
        self._depth = depth
        # self._only_leafs = only_leafs
        self._only_leaves = only_leaves
        self._fields = None
        self._ffilters: List[FieldFilterFunctionType] = []

    def __iter__(self):
        if self._fields is None:
            self._fields = self._build_fields([], self._model, (), self._depth, 0)

        return iter(self._fields)

    def _build_fields(self, fields_info, model, parents_fields, rem_depth, depth):
        "@param rem_depth: Remaining depth to look into."
        ffilters = self._ffilters
        include_fk = not self._only_leaves
        deeper_fields_args = []
        meta = model._meta

        for field in chain(meta.fields, meta.many_to_many):
            # if all(ffilter(field, depth) for ffilter in ffilters):
            if all(ffilter(model=model, field=field, depth=depth) for ffilter in ffilters):
                field_info = (*parents_fields, field)

                if field.is_relation:  # TODO: and field.related_model ? not auto_created ?
                    if rem_depth:
                        if include_fk:
                            fields_info.append(field_info)
                        deeper_fields_args.append((field.remote_field.model, field_info))
                    elif include_fk:
                        fields_info.append(field_info)
                else:
                    fields_info.append(field_info)

        # Fields of related model are displayed at the end
        for sub_model, field_info in deeper_fields_args:
            self._build_fields(fields_info, sub_model, field_info, rem_depth - 1, depth + 1)

        return fields_info

    def filter(self, function: Optional[FieldFilterFunctionType] = None, **kwargs):
        """Filter the field sequence.
        @param function: (optional) Callable which takes 3 keyword arguments
               ("model", "field" & "depth"), and returns a boolean
               ('True' means 'the field is accepted').
        @param kwargs: Keywords can be a true field attribute name, or a creme tag.
               Eg: ModelFieldEnumerator(Contact).filter(editable=True, viewable=True)
        """
        self._ffilters.append(_FilterModelFieldQuery(function, **kwargs))
        return self

    def exclude(self, function: Optional[FieldFilterFunctionType] = None, **kwargs):
        """Exclude some fields from the sequence.
        @see ModelFieldEnumerator.filter()
        """
        self._ffilters.append(_ExcludeModelFieldQuery(function, **kwargs))
        return self

    def choices(self, printer=lambda field: str(field.verbose_name)) -> List[Tuple[str, str]]:
        """@return A list of tuple (field_name, field_verbose_name)."""
        sort_key = collator.sort_key
        sortable_choices = []

        # We sort the choices by their value (alphabetical order), with first fields,
        # then sub-fields (fields of ForeignKey/ManyToManyField), then sub-sub-fields...
        for fields_info in self:
            # These variable avoid gettext/printer to be called too many times
            fk_vnames = [str(field.verbose_name) for field in fields_info[:-1]]
            terminal_vname = str(printer(fields_info[-1]))

            # The sort key (list.sort() will compare tuples, so the first elements,
            # then eventually the second ones etc...)
            key = (
                len(fields_info),  # NB: ensure that fields are first, then sub-fields...
                *(sort_key(vname) for vname in fk_vnames),
                sort_key(terminal_vname),
            )
            # A classical django choice. Eg: ('user__email', '[Owner user] - Email address')
            choice = (
                '__'.join(field.name for field in fields_info),
                ' - '.join(chain((f'[{vname}]' for vname in fk_vnames), [terminal_vname]))
            )

            sortable_choices.append((key, choice))

        sortable_choices.sort(key=lambda c: c[0])  # Sort with our previously computed key

        return [c[1] for c in sortable_choices]  # Extract choices

    @property
    def model(self):
        return self._model


# OrderedField -----------------------------------------------------------------

class Order:
    "Represents DB order: ASC or DESC."
    __slots__ = ('asc', )

    def __init__(self, asc: bool = True):
        """Constructor.

         @param asc: Boolean. True==ASC / False==DESC .
        """
        self.asc = asc

    def __str__(self):
        return 'ASC' if self.asc else 'DESC'

    @property
    def desc(self) -> bool:
        return not self.asc

    @classmethod
    def from_string(cls, value: str, required: bool = True):
        """Build an Order instance from a string.

        @param value: String in ('ASC', 'DESC').
        @param required: Boolean. (default:True). If False, empty values are
               accepted for the "value" argument.
        @return: An Order instance.
        @raise ValueError: invalid "value" argument.
        """
        if value == 'ASC':
            asc = True
        elif value == 'DESC':
            asc = False
        else:
            if required or value not in EMPTY_VALUES:
                raise ValueError(f'Order value must be ASC or DESC (value={value})')

            asc = True

        return cls(asc)

    @property
    def prefix(self) -> str:
        """Get the string prefix to use before field name in some places
        like order_by() methods.
        """
        return '' if self.asc else '-'

    def reverse(self) -> None:
        "Reverse the order (in-place)."
        self.asc = not self.asc

    def reversed(self):
        "Get a reversed instance of Order."
        return self.__class__(not self.asc)


class OrderedField:
    """Represents a model-field name with an optional order prefix "-"
    (like in <MyModel._meta.ordering> or in <MyModel.objects.order_by()>).
    """
    def __init__(self, ord_field_str: str):
        """Constructor.

        @param ord_field_str: String ; something like 'name' or '-creation_date'.
        """
        self._raw = ord_field_str

        if ord_field_str.startswith('-'):
            self.field_name = ord_field_str[1:]
            asc = False
        else:
            self.field_name = ord_field_str
            asc = True

        self.order = Order(asc)

    def __str__(self):
        return self._raw

    # TODO: def reverse ?

    def reversed(self):
        """Returns the _OrderedField instance corresponding to the same field
        but with a reversed order.
        """
        return self.__class__(self.order.reversed().prefix + self.field_name)
