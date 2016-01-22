# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from functools import partial
from itertools import chain
import warnings

from django.db.models import ForeignKey, ManyToManyField, FieldDoesNotExist, DateField

from .unicode_collation import collator


# TODO; used only in activesync
# TODO: manage better M2M values
def get_instance_field_info(obj, field_name):
    """ For a field_name 'att1__att2__att3', it searches and returns the tuple
    (class of obj.att1.att2.get_field('att3'), obj.att1.att2.att3)
    @return : (field_class, field_value)
    """
    subfield_names = field_name.split('__')

    try:
        for subfield_name in subfield_names[:-1]:
            obj = getattr(obj, subfield_name)  # Can be None if a M2M has no related value

        subfield_name = subfield_names[-1]
        field_class = obj._meta.get_field(subfield_name).__class__
        field_value = getattr(obj, subfield_name)

        if issubclass(field_class, ManyToManyField):
            field_value = field_value.all()

        return field_class, field_value
    except (AttributeError, FieldDoesNotExist):
        return None, ''


class FieldInfo(object):
    __slots__ = ('__fields', )

    def __init__(self, model, field_name):
        "@throws FieldDoesNotExist"
        self.__fields = fields = []
        subfield_names = field_name.split('__')

        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            rel = getattr(field, 'rel', None)

            if rel is None:
                raise FieldDoesNotExist('"%s" is not a ForeignKey/ManyToManyField,'
                                        ' so it can have a sub-field' % subfield_name
                                       )

            model = rel.to
            fields.append(field)

        fields.append(model._meta.get_field(subfield_names[-1]))

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            # We avoid the call to __init__ and its introspection work
            fi = FieldInfo.__new__(FieldInfo)
            fi.__fields = self.__fields[idx]

            return fi

        return self.__fields[idx]

    def __len__(self):
        return len(self.__fields)

    def __iter__(self):
        return iter(self.__fields)

    @property
    def verbose_name(self):
        return u' - '.join(unicode(field.verbose_name) for field in self.__fields)


def is_date_field(field):
    return isinstance(field, DateField)


def get_date_fields(model, exclude_func=lambda f: False):
    warnings.warn("get_date_fields() function is deprecated (because it is probably useless).",
                  DeprecationWarning
                 )
    return [field for field in model._meta.fields if is_date_field(field) and not exclude_func(field)]


# ModelFieldEnumerator -------------------------------------------------------
class _FilterModelFieldQuery(object):
    # TODO: use a constants in fields_tags ?? set() ?
    _TAGS = ('viewable', 'clonable', 'enumerable', 'optional')

    def __init__(self, function=None, **kwargs):
        self._conditions = conditions = []

        if function:
            conditions.append(function)

        for attr_name, value in kwargs.iteritems():
            fun = (lambda field, deep, attr_name, value: field.get_tag(attr_name) == value) \
                  if attr_name in self._TAGS else \
                  (lambda field, deep, attr_name, value: getattr(field, attr_name) == value)

            conditions.append(partial(fun, attr_name=attr_name, value=value))

    def __call__(self, field, deep):
        return all(cond(field, deep) for cond in self._conditions)


class _ExcludeModelFieldQuery(_FilterModelFieldQuery):
    def __call__(self, field, deep):
        return not any(cond(field, deep) for cond in self._conditions)


class ModelFieldEnumerator(object):
    def __init__(self, model, deep=0, only_leafs=True):
        """Constructor.
        @param model DjangoModel class.
        @param deep Deep of the returned fields (0=fields of the class, 1=also
                    the fields of directly related classes, etc...).
        @param only_leafs If True, FK/M2M fields are not returned (but eventually,
                          their sub-fields, depending of the 'deep' paramater of course).
        """
        self._model = model
        self._deep = deep
        self._only_leafs = only_leafs
        self._fields = None
        self._ffilters = []

    def __iter__(self):
        if self._fields is None:
            self._fields = self._build_fields([], self._model, (), self._deep, 0)

        return iter(self._fields)

    def _build_fields(self, fields_info, model, parents_fields, rem_depth, depth):
        "@param rem_depth Remaining depth to look into"
        ffilters = self._ffilters
        include_fk = not self._only_leafs
        deeper_fields_args = []
        meta = model._meta

        for field in chain(meta.fields, meta.many_to_many):
            if all(ffilter(field, depth) for ffilter in ffilters):
                field_info = parents_fields + (field,)

                if isinstance(field, (ForeignKey, ManyToManyField)):
                    if rem_depth:
                        if include_fk:
                            fields_info.append(field_info)
                        deeper_fields_args.append((field.rel.to, field_info))
                    elif include_fk:
                        fields_info.append(field_info)
                else:
                    fields_info.append(field_info)

        # Fields of related model are displayed at the end
        for sub_model, field_info in deeper_fields_args:
            self._build_fields(fields_info, sub_model, field_info, rem_depth - 1, depth + 1)

        return fields_info

    def filter(self, function=None, **kwargs):
        """Filter the field sequence.
        @param function Callable which takes 2 arguments (field instance, deep),
                        and returns a boolean ('True' means 'the field is accepted').
        @param kwargs Keywords can be a true field attribute name, or a creme tag.
               Eg: ModelFieldEnumerator(Contact).filter(editable=True, viewable=True)
        """
        self._ffilters.append(_FilterModelFieldQuery(function, **kwargs))
        return self

    def exclude(self, function=None, **kwargs):
        """See ModelFieldEnumerator.filter()"""
        self._ffilters.append(_ExcludeModelFieldQuery(function, **kwargs))
        return self

    def choices(self, printer=lambda field: unicode(field.verbose_name)):
        """@return A list of tuple (field_name, field_verbose_name)."""
        sort_key = collator.sort_key
        sortable_choices = []

        # We sort the choices by their value (alphabetical order), with first fields,
        # then sub-fields (fields of ForeignKey/ManyToManyField), then sub-sub-fields...
        for fields_info in self:
            # These variable avoid ugettext/printer to be called to many times
            fk_vnames = [unicode(field.verbose_name) for field in fields_info[:-1]]
            terminal_vname = unicode(printer(fields_info[-1]))

            # The sort key (list.sort() will compare tuples, so the first elements,
            # then eventually the second ones etc...)
            key = tuple(chain([len(fields_info)],  # NB: ensure that fields are first, then sub-fields...
                              (sort_key(vname) for vname in fk_vnames),
                              [sort_key(terminal_vname)]
                             )
                       )
            # A classical django choice. Eg: ('user__email', '[Owner user] - Email address')
            choice = ('__'.join(field.name for field in fields_info),
                      u' - '.join(chain((u'[%s]' % vname for vname in fk_vnames),
                                        [terminal_vname]
                                       )
                                 )
                     )

            sortable_choices.append((key, choice))

        sortable_choices.sort(key=lambda c: c[0])  # Sort with our previously computed key

        return [c[1] for c in sortable_choices]  # Extract choices
