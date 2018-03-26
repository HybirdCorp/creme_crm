# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2018 Hybird
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
# import warnings

from django.db.models import FieldDoesNotExist, DateField

from .unicode_collation import collator


# def get_instance_field_info(obj, field_name):
#     """ For a field_name 'att1__att2__att3', it searches and returns the tuple
#     (class of obj.att1.att2.get_field('att3'), obj.att1.att2.att3)
#     @return : (field_class, field_value)
#     """
#     warnings.warn("get_instance_field_info() function is deprecated ; use FieldInfo.value_from() instead.",
#                   DeprecationWarning
#                  )
#
#     subfield_names = field_name.split('__')
#
#     try:
#         for subfield_name in subfield_names[:-1]:
#             obj = getattr(obj, subfield_name)  # Can be None if a M2M has no related value
#
#         subfield_name = subfield_names[-1]
#         field = obj._meta.get_field(subfield_name)
#         field_value = getattr(obj, subfield_name)
#
#         if field.many_to_many:
#             field_value = field_value.all()
#
#         return field.__class__, field_value
#     except (AttributeError, FieldDoesNotExist):
#         return None, ''


class FieldInfo(object):
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
    so naturally the fields which can have "sub-fields" are fields like ForeignKeys or ManyToManyFields.
    """
    __slots__ = ('_model', '__fields')

    def __init__(self, model, field_name):
        """ Constructor.

        @param model: Class inheriting django.db.models.Model.
        @param field_name: String representing a 'chain' of fields; eg: 'book__author__name'.
        @throws FieldDoesNotExist
        """
        self._model = model
        self.__fields = fields = []
        subfield_names = field_name.split('__')

        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            # rel = getattr(field, 'rel', None)
            remote_field = getattr(field, 'remote_field', None)

            # if rel is None:
            if remote_field is None:
                raise FieldDoesNotExist('"%s" is not a ForeignKey/ManyToManyField,'
                                        ' so it can have a sub-field' % subfield_name
                                       )

            # model = rel.to
            model = remote_field.model
            fields.append(field)

        fields.append(model._meta.get_field(subfield_names[-1]))

    def __getitem__(self, idx):
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
                    # fi._model = self.__fields[idx.start - 1].rel.to
                    fi._model = self.__fields[idx.start - 1].remote_field.model
                except IndexError:
                    pass

            return fi

        return self.__fields[idx]

    def __nonzero__(self):
        return bool(self.__fields)

    def __len__(self):
        return len(self.__fields)

    def __iter__(self):
        return iter(self.__fields)

    def __repr__(self):
        return 'FieldInfo(model=%s, field_name="%s")' % (
                    self._model.__name__,
                    '__'.join(f.name for f in self.__fields),
                )

    @property
    def model(self):
        return self._model

    @property
    def verbose_name(self):
        return u' - '.join(unicode(field.verbose_name) for field in self.__fields)

    # TODO: probably does not work with several ManyToManyFields in the fields chain
    def value_from(self, instance):
        if not isinstance(instance, self._model):
            raise ValueError('"%s" is not an instance of %s' % (instance, self._model))

        result = instance

        for subfield in self:
            if result is None:
                break

            if isinstance(result, list):
                result = [getattr(elt, subfield.name) for elt in result]
            else:
                result = getattr(result, subfield.name)

                if subfield.many_to_many:
                    result = list(result.all())

        return result


def is_date_field(field):
    return isinstance(field, DateField)


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

                if field.is_relation:  # TODO: and field.related_model ? not auto_created ?
                    if rem_depth:
                        if include_fk:
                            fields_info.append(field_info)
                        # deeper_fields_args.append((field.rel.to, field_info))
                        deeper_fields_args.append((field.remote_field.model, field_info))
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
        """Exclude some fiels from the sequence.
        @see ModelFieldEnumerator.filter()
        """
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
