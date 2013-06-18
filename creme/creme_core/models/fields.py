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


from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db.models import DateTimeField, CharField, ForeignKey, SET
from django.utils.timezone import now


#TODO: add a form field ?? (validation)
#TODO: fix the max_lenght value ?,
class PhoneField(CharField):
    def south_field_triple(self):
        """Field description for South. (see http://south.aeracode.org/docs/customfields.html#south-field-triple)"""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.CharField"
        args, kwargs = introspector(self)

        return (field_class, args, kwargs)

#TODO: Make a real api for this
class DurationField(CharField):
    #TODO: factorise
    def south_field_triple(self):
        """Field description for South. (see http://south.aeracode.org/docs/customfields.html#south-field-triple)"""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.CharField"
        args, kwargs = introspector(self)

        return (field_class, args, kwargs)


def _transfer_assignation():
    return CremeUserForeignKey._TRANSFER_TO_USER

class CremeUserForeignKey(ForeignKey):
    _TRANSFER_TO_USER = None

    def __init__(self, **kwargs):
        kwargs['on_delete'] = SET(_transfer_assignation)#Overide on_delete, even if it was already defined in kwargs
        super(CremeUserForeignKey, self).__init__(User, **kwargs)

    def get_internal_type(self):
        return "ForeignKey"

    def south_field_triple(self):
        """Field description for South. (see http://south.aeracode.org/docs/customfields.html#south-field-triple)"""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)

        return (field_class, args, kwargs)


class CTypeForeignKey(ForeignKey):
    def __init__(self, **kwargs):
        kwargs['to'] = ContentType
        super(CTypeForeignKey, self).__init__(**kwargs)

    def __get__(self, instance, instance_type=None):
        #return ContentType.objects.get_for_id(getattr(instance, self.attname))
        ct_id = getattr(instance, self.attname)
        return ContentType.objects.get_for_id(ct_id) if ct_id else None

    def __set__(self, instance, value):
        #TODO: accept model directly + get_for_model() ??
        setattr(instance, self.attname, value.id if value else value)

    def contribute_to_class(self, cls, name):
        super(CTypeForeignKey, self).contribute_to_class(cls, name)

        #Connect self as the descriptor for this field (thx to GenericForeignKey code)
        setattr(cls, name, self)

    #TODO: factorise
    def get_internal_type(self):
        return "ForeignKey"

    def south_field_triple(self):
        from south.modelsinspector import introspector
        field_class = 'django.db.models.fields.related.ForeignKey'
        args, kwargs = introspector(self)

        return (field_class, args, kwargs)


# Code copied/modified from django_extensions one:
#    http://code.google.com/p/django-command-extensions/

################################################################################
#  Copyright (c) 2007 Michael Trier
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
################################################################################

class CreationDateTimeField(DateTimeField):
    """ CreationDateTimeField

    By default, sets editable=False, blank=True, default=now
    """
    def __init__(self, *args, **kwargs):
        setdefault = kwargs.setdefault
        setdefault('editable', False)
        setdefault('blank',    True)
        setdefault('default',  now)

        super(CreationDateTimeField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "DateTimeField"

    def south_field_triple(self):
        """Returns a suitable description of this field for South."""
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.DateTimeField"
        args, kwargs = introspector(self)

        return (field_class, args, kwargs)


class ModificationDateTimeField(CreationDateTimeField):
    """ ModificationDateTimeField

    By default, sets editable=False, blank=True, default=now

    Sets value to now() on each save of the model.
    """

    def pre_save(self, model, add):
        value = now()
        setattr(model, self.attname, value)

        return value
