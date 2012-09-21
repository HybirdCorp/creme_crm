# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

#thanks to Olivier Meunier 

from django.db import models
from django.utils.functional import curry


def contribute_to_model(contrib, destination, fields_2_delete=()):
    """
    Update ``contrib`` model based on ``destination``.

    Every new field will be created. Existing fields will have some properties
    updated.

    Methods and properties of ``contrib`` will populate ``destination``.

    Usage example:

    >>> from django.contrib.auth.models import User
    >>> from django.db import models
    >>> 
    >>> class MyUser(models.Model):
    >>>     class Meta:
    >>>         abstract = True
    >>>         db_table = 'user' # new auth_user table name
    >>>
    >>>     # New field
    >>>     phone = models.CharField('phone number', blank=True, max_length=20)
    >>> 
    >>>     # Email could be null
    >>>     email = models.EmailField(blank=True, null=True)
    >>>
    >>>     # New (stupid) method
    >>>     def get_phone(self):
    >>>         return self.phone
    >>> 
    >>> contribute_to_model(MyUser, User, fields_2_delete=('is_staff',))
    """
    # Contrib should be abstract
    if not contrib._meta.abstract:
        raise ValueError('Your contrib model should be abstract.')

    protected_get_display_method = []
    # Update or create new fields
    for field in contrib._meta.fields:
        try:
            destination._meta.get_field_by_name(field.name)
        except models.FieldDoesNotExist:
            field.contribute_to_class(destination, field.name)
            if field.choices:
                setattr(destination, 'get_%s_display' % field.name, curry(destination._get_FIELD_display, field=field))
                protected_get_display_method.append('get_%s_display' % field.name)
        else:
            current_field = destination._meta.get_field_by_name(field.name)[0]
            current_field.null = field.null
            current_field.blank = field.blank
            current_field.max_length = field.max_length

    # Change some meta information
    if hasattr(contrib.Meta, 'db_table'):
        destination._meta.db_table = contrib._meta.db_table

    # Add (or replace) properties and methods
    protected_items = dir(models.Model) + ['Meta', '_meta'] + protected_get_display_method #TODO: use a set() ??

    for k, v in contrib.__dict__.items(): #TODO: iteritems() instead ??
        if k not in protected_items:
            setattr(destination, k, v)

    # Deletion of unwanted fields
    delete_model_fields(destination, *fields_2_delete)

def delete_model_fields(model, *field_names):
    """Remove some django.db.models.Fields instance from a django.db.Model
    @param field_names Sequence of strings
    """
    meta = model._meta
    local_fields = meta.local_fields

    for field in [f for f in local_fields if f.name in field_names]:
        local_fields.remove(field)

    if hasattr(meta, '_field_name_cache'):
        del meta._field_name_cache
