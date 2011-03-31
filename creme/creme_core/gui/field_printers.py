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

from creme_core.models import fields

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
def get_foreign_key_popup_str(x):
    if hasattr(x, 'get_absolute_url') and hasattr(x, 'entity_type'):
        return '<a href="%s"><u>%s</u></a>' % (x.get_absolute_url(), x)
    return '%s' % x if x else ''

def simple_print(x):
    return '%s' % escape(x) if x is not None else ""

def print_image(x):
    url = x.url
    return """<a href="javascript:openWindow('%s','image_popup');"><img src="%s" %s alt="%s"/></a>""" % \
            (url, url, image_size(x), url)     #TODO: use dict instead of tuple ?

def print_urlfield(x):
    esc_x = escape(x)
    return '<a href="%s" target="_blank">%s</a>' % (esc_x, esc_x)

def print_datetime(x):
    return date_format(x, 'DATETIME_FORMAT') if x else ''

def print_date(x):
    return date_format(x, 'DATE_FORMAT') if x else ''

IMAGES_ATTRIBUTES = {Image: 'image'}

#TODO: clean (IMAGES_ATTRIBUTES really useful ???)
#TODO: use string.join()
def get_m2m_popup_str(x):
    result   = '<ul>'
    img_attr = IMAGES_ATTRIBUTES.get(x.model)

    if img_attr is not None:
        for a in x.all():
            esc_a = escape(a)
            result += '<li><img src="%s" alt="%s" title="%s" %s class="magnify"/></li>' % \
                      (a.__getattribute__(img_attr).url, esc_a, esc_a, image_size(a, 80, 80)) #TODO use dict, getattr too
    else:
        for a in x.all():
            if hasattr(a, 'get_absolute_url'):
                result += '<li><a target="_blank" href="%s">%s</li></a>' % (a.get_absolute_url(), escape(a))
            else:
                result += '<li>%s</li>' % escape(a)
    result += '</ul>'

    return result

field_printers_registry = {
     models.AutoField:                  simple_print,
     models.BooleanField:               lambda x: '<input type="checkbox" value="%s" %s disabled/>' % (escape(x), 'checked' if x else ''),
     models.CharField:                  simple_print,
     models.CommaSeparatedIntegerField: simple_print,
     models.DateField:                  print_date,
     models.DateTimeField:              print_datetime,
     models.DecimalField:               simple_print,
     models.EmailField:                 lambda a: '<a href="mailto:%s">%s</a>' % (a, a) if a else '',
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
