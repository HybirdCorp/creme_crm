# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db import models
from django.db.models import ForeignKey, ManyToManyField, FieldDoesNotExist #Field
from django.conf import settings

from ..models import CremeEntity


class NotDjangoModel(Exception):
    pass

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

def get_model_field_info(model, field_name, silent=True):
    """ For a field_name 'att1__att2__att3', it returns the list of dicts
        [
         {'field': django.db.models.fields.related.ForeignKey for model.att1, 'model': YourModelClass for model.att1},
         {'field': django.db.models.fields.related.ForeignKey for model.att2, 'model': YourModelClass for model.att2},
         {'field': django.db.models.fields.FieldClass for model.att3,         'model': None},
        ]
    """
    subfield_names = field_name.split('__')
    info = []

    try:
        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            model = field.rel.to
            info.append({'field': field, 'model': model})

        field = model._meta.get_field(subfield_names[-1])
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
    fields = get_model_field_info(model, field_name, silent)
    return separator.join([unicode(f['field'].verbose_name) for f in fields])

#def get_function_field_verbose_name(model, function_name):
    #"""
        #@Returns : function field's verbose name if found else None
        #/!\ Model has to be a subclass of CremeAbstractEntity
    #"""
    #f_field = model.function_fields.get(function_name)

    #if f_field:
        #return unicode(f_field.verbose_name)

#def get_related_field_verbose_name(model, related_field_name):
    #"""@returns the verbose name of the model of the related field or None"""
    #for related_field in model._meta.get_all_related_objects():
        #if related_field.var_name == related_field_name:
            #return unicode(related_field.model._meta.verbose_name)

def get_related_field(model, related_field_name):
    #TODO: use find_first
    for related_field in model._meta.get_all_related_objects():
        if related_field.var_name == related_field_name:
            return related_field

def _get_entity_column(entity, column_name, field_class):
    fields_names = [] #TODO: slice once at the end instead of several append()...
    cols = column_name.split('__')

    for i, f_info in enumerate(get_model_field_info(entity.__class__, column_name)):
        fields_names.append(cols[i])

        if issubclass(f_info['field'].__class__, field_class):
            break

    return ('__'.join(fields_names), cols[len(cols)-i-1:])

#def get_fk_entity(entity, column_name, get_value=False, user=None):
    #"""Get the first foreign key entity found in the column_name path
        #entity=Contact(), column_name='photo__name' returns entity.photo
        #if get_value returns the value i.e : entity.photo.name
        #if get_value and user returns the value if the user can read it else settings.HIDDEN_VALUE
            #NB: If not get_value the fk is returned no matter what
    #"""
    #fk_column, rest = _get_entity_column(entity, column_name, ForeignKey)
    #if get_value:
        #fk = getattr(entity, fk_column)

        #if isinstance(fk, CremeEntity) and user is not None and not user.has_perm_to_view(fk):
            #return settings.HIDDEN_VALUE

        ##return getattr(fk, '__'.join(rest))
        #return getattr(fk, '__'.join(rest)) if fk else fk #TODO: split, join again == ugly

    #return getattr(entity, fk_column)

#TODO: used only once => remove ?
#TODO: rename
#TODO: get_value + get_value_func args ??
#TODO: compose 2 functions to 'stringyfy' instances insted of give get_value_func ??
def get_m2m_entities(entity, column_name, get_value=False, q_filter=None,
                     get_value_func=lambda values: u', '.join(values), user=None):
    """Get the first many to many entity found in the column_name path
        entity=Contact(), column_name='photos__name' returns entity.photos.all()
        if get_value returns the values i.e : [e.name for e in entity.photos.all()]

        if get_value and user returns the values and replaces values that the user can't view by settings.HIDDEN_VALUE
            NB: If not get_value, entities are NOT filtered by credentials => TODO/Usefull?
    """
    m2m_column, rest = _get_entity_column(entity, column_name, ManyToManyField)
    m2m_field = getattr(entity, m2m_column)
    #TODO: m2m_field = getattr(entity, m2m_column, None) to not raise exception when m2m is empty ??

    if q_filter is not None:
        m2m_instances = m2m_field.filter(q_filter)
    else:
        m2m_instances = m2m_field.all()

    if get_value:
        #has_to_check_view_perms = issubclass(m2m_field.model, CremeEntity) and user is not None
        #rest = u'__'.join(rest)
        #values = []

        #if has_to_check_view_perms:
            #HIDDEN_VALUE = settings.HIDDEN_VALUE

            #for m in m2m_instances:
                #if user.has_perm_to_view(m):
                    #attr = getattr(m, rest, None) or u''
                #else:
                    #attr = HIDDEN_VALUE

                #values.append(unicode(attr))
        #else:
            #for m in m2m_instances:
                #attr = getattr(m, rest, None) or u''
                #values.append(unicode(attr))

        #return get_value_func(values)

        rest = u'__'.join(rest)

        #TODO: assert that user is not None when CremeEntity ???
        if issubclass(m2m_field.model, CremeEntity) and user is not None: #has to check 'view' perms
            HIDDEN_VALUE = settings.HIDDEN_VALUE
            has_perm = user.has_perm_to_view
            extract_value = lambda m: (getattr(m, rest, None) or u'') if has_perm(m) else HIDDEN_VALUE
        else:
            extract_value = lambda m: getattr(m, rest, None) or u''

        return get_value_func(unicode(extract_value(m)) for m in m2m_instances)

    return m2m_instances

#def filter_entities_on_ct(entities, ct):
    #ct_model_class = ct.model_class()
    #return [entity for entity in entities if isinstance(entity, ct_model_class)]

def is_date_field(field):
    return isinstance(field, (models.DateTimeField, models.DateField))

def get_date_fields(model, exclude_func=lambda f: False):
    return [field for field in model._meta.fields if is_date_field(field) and not exclude_func(field)]



class _FilterModelFieldQuery(object):
    _TAGS = ('viewable', 'clonable', 'enumerable') #TODO: use a constants in fields_tags ??

    def __init__(self, function=None, **kwargs):
        self._conditions = conditions = []

        if function:
            conditions.append(function)

        for attr_name, value in kwargs.iteritems():
            fun = (lambda field, attr_name, value: field.get_tag(attr_name) == value) if attr_name in self._TAGS else \
                  (lambda field, attr_name, value: getattr(field, attr_name) == value)

            conditions.append(partial(fun, attr_name=attr_name, value=value))

    def __call__(self, field):
        return all(cond(field) for cond in self._conditions)


class _ExcludeModelFieldQuery(_FilterModelFieldQuery):
    def __call__(self, field):
        return not any(cond(field) for cond in self._conditions)


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
            self._fields = self._build_fields([], self._model, (), self._deep)

        return iter(self._fields)

    def _build_fields(self, fields_info, model, parents_fields, deep):
        ffilters = self._ffilters
        include_fk = not self._only_leafs
        deeper_fields_args = []
        meta = model._meta

        for field in chain(meta.fields, meta.many_to_many):
            if all(ffilter(field) for ffilter in ffilters):
                field_info = parents_fields + (field,)

                if field.get_internal_type() in ('ForeignKey', 'ManyToManyField'):
                    if deep:
                        if include_fk:
                            fields_info.append(field_info)
                        deeper_fields_args.append((field.rel.to, field_info))
                    elif include_fk:
                        fields_info.append(field_info)
                else:
                    fields_info.append(field_info)

        # Fields of related model are displayed at the end
        for sub_model, field_info in deeper_fields_args:
            self._build_fields(fields_info, sub_model, field_info, deep - 1)

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
