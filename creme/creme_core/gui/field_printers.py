# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.utils.html import escape
from django.utils.formats import date_format
from django.utils.safestring import mark_safe

from creme_core.models import CremeEntity, fields
from creme_core.utils.meta import get_field_infos, get_model_field_infos, get_m2m_entities

from media_managers.models import Image #TODO: remove dependancy


#TODO: in settings
MAX_HEIGHT = 200
MAX_WIDTH = 200

def image_size(image, max_h=MAX_HEIGHT, max_w=MAX_WIDTH):
    if hasattr(image, 'height'):
        h = image.height
    elif hasattr(image, 'height_field'):
        h = image.height_field
    else:
        h = max_h
    if hasattr(image, 'width'):
        w = image.width
    elif hasattr(image, 'width_field'):
        w = image.width_field
    else:
        w = max_w

    h = float(h)
    w = float(w)

    ratio = max(h / max_h, w / max_w)

    if ratio >= 1.0:
        h /= ratio
        w /= ratio

    return "height=%s width=%s" % (h, w)

#TODO: recode.. use/factorise with allowed unicode tag ???
def get_foreign_key_popup_str(entity, fval):
    #if hasattr(fval, 'get_absolute_url') and hasattr(fval, 'entity_type'):
    if isinstance(fval, CremeEntity):
        return '<a href="%s"><u>Entity#%s</u></a>' % (fval.get_absolute_url(), fval.id) #TODO creds

    #return '%s' % fval if fval else ''
    return str(fval) if fval else '' #TODO: unicode ??

def simple_print(entity, fval):
    return '%s' % escape(fval) if fval is not None else ""

def print_image(entity, fval):
    return """<a href="javascript:openWindow('%(url)s','image_popup');"><img src="%(url)s" %(size)s alt="%(url)s"/></a>""" % {
                'url':  fval.url,
                'size': image_size(fval),
            }

def print_urlfield(entity, fval):
    esc_fval = escape(fval)
    return '<a href="%s" target="_blank">%s</a>' % (esc_fval, esc_fval)

def print_datetime(entity, fval):
    return date_format(fval, 'DATETIME_FORMAT') if fval else ''

def print_date(entity, fval):
    return date_format(fval, 'DATE_FORMAT') if fval else ''

IMAGES_ATTRIBUTES = {Image: 'image'}

#TODO: clean (IMAGES_ATTRIBUTES really useful ???)
#TODO: use string.join()
def get_m2m_popup_str(entity, fval):
    result   = '<ul>'
    img_attr = IMAGES_ATTRIBUTES.get(fval.model)

    if img_attr is not None:
        for a in fval.all():
            esc_a = escape(a)
            result += '<li><img src="%s" alt="%s" title="%s" %s class="magnify"/></li>' % \
                      (a.__getattribute__(img_attr).url, esc_a, esc_a, image_size(a, 80, 80)) #TODO use dict, getattr too
    else:
        for a in fval.all():
            if hasattr(a, 'get_absolute_url'):
                result += '<li><a target="_blank" href="%s">%s</li></a>' % (a.get_absolute_url(), escape(a)) #TODO: creds
            else:
                result += '<li>%s</li>' % escape(a)
    result += '</ul>'

    return result

class _FieldPrintersRegistry(object):
    def __init__(self):
        self._printers = {
            models.AutoField:                  simple_print,
            models.BooleanField:               lambda entity, fval: '<input type="checkbox" value="%s" %s disabled/>' % (escape(fval), 'checked' if fval else ''),
            models.CharField:                  simple_print,
            models.CommaSeparatedIntegerField: simple_print,
            models.DateField:                  print_date,
            models.DateTimeField:              print_datetime,
            models.DecimalField:               simple_print,
            models.EmailField:                 lambda entity, fval: '<a href="mailto:%s">%s</a>' % (fval, fval) if fval else '',
            models.FileField:                  simple_print,
            models.FilePathField:              simple_print,
            models.FloatField:                 simple_print,
            models.ImageField:                 print_image,
            models.IntegerField:               simple_print,
            models.IPAddressField:             simple_print,
            models.NullBooleanField:           simple_print,
            models.PositiveIntegerField:       simple_print,
            models.PositiveSmallIntegerField:  simple_print,
            models.SlugField:                  simple_print,
            models.SmallIntegerField:          simple_print,
            models.TextField:                  simple_print,
            models.TimeField:                  simple_print,
            models.URLField:                   print_urlfield,
            models.XMLField:                   simple_print,
            models.ForeignKey:                 get_foreign_key_popup_str,
            models.ManyToManyField:            get_m2m_popup_str,
            models.OneToOneField:              get_foreign_key_popup_str,

            fields.PhoneField:                 simple_print,
            fields.ModificationDateTimeField:  print_datetime,
            fields.CreationDateTimeField :     print_datetime,
        }

    def register(self, field, printer):
        """Register a field printer.
        @param field A class inheriting django.models.Field
        @param printer A callable with 2 parameter: 'entity' & 'fval'. See simple_print, print_urlfield etc...
        """
        self._printers[field] = printer

    def get_html_field_value(self, entity, field_name):
        field_class, field_value = get_field_infos(entity, field_name)

        if field_class is None:
            fields_through = [f['field'].__class__ for f in get_model_field_infos(entity.__class__, field_name)]

            if models.ManyToManyField in fields_through: #TODO: use any() instead
                return get_m2m_entities(entity, field_name, get_value=True,
                                        get_value_func=lambda values: ", ".join([val for val in values if val])  #TODO: use (i)filter
                                       )

        print_func = self._printers.get(field_class)

        if print_func:
            return mark_safe(print_func(entity, field_value))

        return field_value


field_printers_registry = _FieldPrintersRegistry()
