# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

#from django.db import models
from django.db.models import ManyToManyField, FieldDoesNotExist, DateField #Field ForeignKey


#TODO; used only in activesync
#TODO: manage better M2M values
def get_instance_field_info(obj, field_name):
    """ For a field_name 'att1__att2__att3', it searchs and returns the tuple
    (class of obj.att1.att2.get_field('att3'), obj.att1.att2.att3)
    @return : (field_class, field_value)
    """
    subfield_names = field_name.split('__')

    try:
        for subfield_name in subfield_names[:-1]:
            obj = getattr(obj, subfield_name) #can be None if a M2M has no related value

        subfield_name = subfield_names[-1]
        field_class = obj._meta.get_field(subfield_name).__class__
        field_value = getattr(obj, subfield_name)

        if issubclass(field_class, ManyToManyField):
            #return (field_class, getattr(obj, subfield_name).all())
            field_value = field_value.all()

        #return (field_class, getattr(obj, subfield_name))
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
            model = field.rel.to
            fields.append(field)

        fields.append(model._meta.get_field(subfield_names[-1]))

    def __getitem__(self, idx):
        return self.__fields[idx]

    def __len__(self):
        return len(self.__fields)

    def __iter__(self):
        return iter(self.__fields)

    @property
    def verbose_name(self):
        return u' - '.join(unicode(field.verbose_name) for field in self.__fields)


def get_model_field_info(model, field_name, silent=True):
    """ For a field_name 'att1__att2__att3', it returns the list of dicts
        [
         {'field': django.db.models.fields.related.ForeignKey for model.att1, 'model': YourModelClass for model.att1},
         {'field': django.db.models.fields.related.ForeignKey for model.att2, 'model': YourModelClass for model.att2},
         {'field': django.db.models.fields.FieldClass for model.att3,         'model': None},
        ]
    """
    warnings.warn("get_model_field_info() method is deprecated; Use FieldInfo class instead",
                  DeprecationWarning
                 )
    subfield_names = field_name.split('__')
    info = []

    try:
        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            model = field.rel.to
            info.append({'field': field, 'model': model})

        field = model._meta.get_field(subfield_names[-1])
        #TODO: isinstance() ?? ManyToManyField too ??
        model = None if not field.get_internal_type() == 'ForeignKey' else field.rel.to
        info.append({'field': field, 'model': model})
    except (AttributeError, FieldDoesNotExist) as e:
        if not silent:
            raise FieldDoesNotExist(e)

    return info

#TODO: rename to 'get_field_verbose_name'
def get_verbose_field_name(model, field_name, separator=" - ", silent=True):
    """ For a field_name 'att1__att2__att3' it returns
        att1_verbose_name - att2_verbose_name - att3_verbose_name
        - is the default separator
    """
    warnings.warn("get_verbose_field_name() method is deprecated; Use FieldInfo class instead",
                  DeprecationWarning
                 )
    fields = get_model_field_info(model, field_name, silent)
    return separator.join([unicode(f['field'].verbose_name) for f in fields])

def get_related_field(model, related_field_name):
    #TODO: use find_first
    for related_field in model._meta.get_all_related_objects():
        if related_field.var_name == related_field_name:
            return related_field

def is_date_field(field):
    #return isinstance(field, (models.DateTimeField, models.DateField))
    return isinstance(field, DateField)

def get_date_fields(model, exclude_func=lambda f: False):
    warnings.warn("get_date_fields() function is deprecated (because it is probably useless).",
                  DeprecationWarning
                 )
    return [field for field in model._meta.fields if is_date_field(field) and not exclude_func(field)]


# ModelFieldEnumerator -------------------------------------------------------
class _FilterModelFieldQuery(object):
    _TAGS = ('viewable', 'clonable', 'enumerable') #TODO: use a constants in fields_tags ??

    def __init__(self, function=None, **kwargs):
        self._conditions = conditions = []

        if function:
            conditions.append(function)

        for attr_name, value in kwargs.iteritems():
            fun = (lambda field, deep, attr_name, value: field.get_tag(attr_name) == value) if attr_name in self._TAGS else \
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
        @param only_leafs If True, FK,M2M fields are not returned (but eventually,
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

                if field.get_internal_type() in ('ForeignKey', 'ManyToManyField'):
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
        """@param kwargs Keywords can be a true field attribute name, or a creme tag.
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
        return [('__'.join(field.name for field in fields_info),
                 ' - '.join(chain((u'[%s]' % field.verbose_name for field in fields_info[:-1]),
                                  [printer(fields_info[-1])]
                                 )
                           )
                ) for fields_info in self
               ]
