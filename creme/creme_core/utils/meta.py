# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db import models
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.base import ModelBase
from django.db.models import Field, FieldDoesNotExist


class NotDjangoModel(Exception):
    pass

#TODO: rename to get_object_field_infos
def get_field_infos(obj, field_name):
    """ For a field_name 'att1__att2__att3', it searchs and returns the tuple
        (obj.att1.att2.att3, obj.att1.att2._meta.att3
        @return : (field_class, field_value)
    """
    subfield_names = field_name.split('__')

    try:
        for subfield_name in subfield_names[:-1]:
            obj = getattr(obj, subfield_name)

        subfield_name = subfield_names[-1]
        field_class = obj._meta.get_field(subfield_name).__class__
        if issubclass(field_class, ManyToManyField):
            return (field_class, getattr(obj, subfield_name).all())
        return (field_class, getattr(obj, subfield_name))
    except (AttributeError, FieldDoesNotExist), e:
        return None, ''

def get_model_field_infos(model, field_name):
    """ For a field_name 'att1__att2__att3', it returns the list of dicts
        [
         {'field': django.db.models.fields.related.ForeignKey for model.att1, 'model': YourModelClass for model.att1},
         {'field': django.db.models.fields.related.ForeignKey for model.att2, 'model': YourModelClass for model.att2},
         {'field': django.db.models.fields.FieldClass for model.att3,         'model': None},
        ]
    """
    subfield_names = field_name.split('__')
    infos = []

    try:
        for subfield_name in subfield_names[:-1]:
            field = model._meta.get_field(subfield_name)
            model = field.rel.to
            infos.append({'field': field, 'model': model})

        field = model._meta.get_field(subfield_names[-1])
        model = None if not field.get_internal_type() == 'ForeignKey' else field.rel.to
        infos.append({'field': field, 'model': model})
    except (AttributeError, FieldDoesNotExist), e:
        pass

    return infos

#TODO: rename to 'get_field_verbose_name'
def get_verbose_field_name(model, field_name, separator=" - "):
    """ For a field_name 'att1__att2__att3' it returns
        att1_verbose_name - att2_verbose_name - att3_verbose_name
        - is the default separator
    """
    fields = get_model_field_infos(model, field_name)
    return separator.join([unicode(f['field'].verbose_name) for f in fields])

def get_function_field_verbose_name(model, function_name):
    """
        @Returns : function field's verbose name if found else None
        /!\ Model has to be a subclass of CremeAbstractEntity
    """
    f_field = model.function_fields.get(function_name)

    if f_field:
        return unicode(f_field.verbose_name)

#TODO: rename......
def get_flds_with_fk_flds(model_klass, deep=1):
    if not isinstance(model_klass, ModelBase):
        raise NotDjangoModel('%s is not an instance of %s' % (model_klass, ModelBase))

    flds = []

    #TODO: exclude_fields = getattr(model_klass, 'extra_filter_exclude_fields', []) instead....
    has_attr = hasattr(model_klass, 'extra_filter_exclude_fields')

    for field in model_klass._meta.fields + model_klass._meta.many_to_many:
        if has_attr and field.name in model_klass.extra_filter_exclude_fields:
            continue

        if deep and field.get_internal_type() == 'ForeignKey':
            if deep == 1:
                flds += field.rel.to._meta.fields
            else: #deep > 1
                flds += get_flds_with_fk_flds(field.rel.to, deep - 1)
        else:
            flds.append(field)

    #TODO: use a getattr( , , []) + extend() + generator expression == one line :)
    if hasattr(model_klass, 'extra_filter_fields'):
        for field in model_klass.extra_filter_fields:
            flds.append(Field(name=field['name'], verbose_name=field['verbose_name']))

    return flds


#TODO: factoriser avec get_flds_with_fk_flds ?? (visitor ??)
#TODO: utilisation bizarre de unicode() ??? '%s' % unicode(foobar), unicode('%s' % foobar)
def get_flds_with_fk_flds_str(model_klass, deep=1, prefix=None, exclude_func=None):
    """
        @Return a list of tuple which are ('field_name','field_verbose_name')
            or ('field_name__subfield_name','field_verbose_name - subfield_verbose_name') for a ForeignKey
    """
    fields = []

    for field in model_klass._meta.fields + model_klass._meta.many_to_many:
        if field.name in model_klass.header_filter_exclude_fields:
            continue

        if exclude_func is not None and exclude_func(field):
            continue

        if deep and field.get_internal_type() in ('ForeignKey', 'ManyToManyField'):
            if deep == 1:
#                fields.extend((
#                                '%s__%s' % (unicode(field.name), unicode(sub_field.name)),
#                                '%s - %s' % (unicode(field.verbose_name).capitalize(), unicode(sub_field.verbose_name).capitalize())
#                              ) for sub_field in field.rel.to._meta.fields if exclude_func is not None and not exclude_func(sub_field) and not (sub_field.get_internal_type() == 'ForeignKey' or sub_field.get_internal_type() == 'ManyToManyField'))

                fields_append = fields.append
                for sub_field in field.rel.to._meta.fields:
                    if exclude_func is not None and exclude_func(sub_field):
                        continue
                        
                    if  sub_field.get_internal_type() in ('ForeignKey', 'ManyToManyField'):
                        continue

                    if hasattr(field.rel.to, 'header_filter_exclude_fields') and sub_field.name in field.rel.to.header_filter_exclude_fields:
                        continue

                    fields_append((
                                    '%s__%s' % (unicode(field.name), unicode(sub_field.name)),
                                    '%s - %s' % (unicode(field.verbose_name).capitalize(), unicode(sub_field.verbose_name).capitalize())
                                  ))
                                  
            else: #deep > 1:
                fields += get_flds_with_fk_flds_str(field.rel.to, deep - 1,
                                                    prefix={'name': '%s' % unicode(field.name), 'verbose_name': '%s' % unicode(field.verbose_name).capitalize()},
                                                    exclude_func=exclude_func)
        elif prefix:
            fields.append((
                            '%s__%s' % (prefix['name'], unicode(field.name)),
                            '%s - %s' % (prefix['verbose_name'], unicode(field.verbose_name).capitalize())
                         ))
        else:
            fields.append((unicode(field.name), unicode('%s - %s' % (model_klass._meta.verbose_name.capitalize(), unicode(field.verbose_name).capitalize()))))

    return fields


def _get_entity_column(entity, column_name, field_class):
    field_infos = get_model_field_infos(entity.__class__, column_name)
    fields_names = []
    cols = column_name.split('__')

    i = 1
    for i, f_info in enumerate(field_infos):
        fields_names.append(cols[i])

        if issubclass(f_info['field'].__class__, field_class):
            break

    return ('__'.join(fields_names), cols[len(cols)-i-1:])

def get_fk_entity(entity, column_name, get_value=False):
    """Get the first foreign key entity found in the column_name path
        entity=Contact(), column_name='photo__name' returns entity.photo
        if get_value returns the value i.e : entity.photo.name
    """
    fk_column, rest = _get_entity_column(entity, column_name, ForeignKey)
    if get_value:
        return getattr(getattr(entity, fk_column), '__'.join(rest))
    
    return getattr(entity, fk_column)

def get_m2m_entities(entity, column_name, get_value=False, q_filter=None, get_value_func=lambda values:", ".join(values)):
    """Get the first many to many entity found in the column_name path
        entity=Contact(), column_name='photos__name' returns entity.photos.all()
        if get_value returns the values i.e : [e.name for e in entity.photos.all()]
    """
    m2m_column, rest = _get_entity_column(entity, column_name, ManyToManyField)

    if q_filter is not None:
        m2m_entities = getattr(entity, m2m_column).filter(q_filter)
    else:
        m2m_entities = getattr(entity, m2m_column).all()

    if get_value:
        rest = u'__'.join(rest)

        values = []
        for m in m2m_entities:
            attr = getattr(m, rest, u"")
            if attr is None:
                attr = u""
            values.append(u"%s" % attr)
        return get_value_func(values)
#        return ", ".join(values)
#            return ",".join([getattr(m, rest, u"") for m in getattr(entity, m2m_column).all()])

    return m2m_entities

def filter_entities_on_ct(entities, ct):
    ct_model_class = ct.model_class()
    return [entity for entity in entities if isinstance(entity, ct_model_class)]

def get_date_fields(model, exclude_func=lambda f: False):
    fields = []
    for field in model._meta.fields:
        if isinstance(field, (models.DateTimeField, models.DateField)) and not exclude_func(field):
            fields.append(field)
    return fields