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

from itertools import chain

from django.db import models
from django.template.defaultfilters import linebreaks
from django.utils.html import escape
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.translation import ungettext, ugettext_lazy as _

from ..models import CremeEntity, fields
from ..utils.meta import get_instance_field_info, get_model_field_info, get_m2m_entities
from ..templatetags.creme_widgets import widget_entity_hyperlink


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

def simple_print(entity, fval, user):
    return unicode(escape(fval)) if fval is not None else ""

def print_image(entity, fval, user):
    return """<a href="javascript:creme.utils.openWindow('%(url)s','image_popup');"><img src="%(url)s" %(size)s alt="%(url)s"/></a>""" % {
                'url':  fval.url,
                'size': image_size(fval),
            }

def print_urlfield(entity, fval, user):
    if not fval:
        return ""

    esc_fval = escape(fval)
    return '<a href="%s" target="_blank">%s</a>' % (esc_fval, esc_fval)

def print_datetime(entity, fval, user):
    return date_format(fval, 'DATETIME_FORMAT') if fval else ''

def print_date(entity, fval, user):
    return date_format(fval, 'DATE_FORMAT') if fval else ''

def print_foreignkey(entity, fval, user):
    if isinstance(fval, CremeEntity):
        #return '<a href="%s"><u>%s</u></a>' % (fval.get_absolute_url(), fval) if fval.can_view(user) else \
               #fval.allowed_unicode(user)
        return widget_entity_hyperlink(fval, user)

    return unicode(fval) if fval else u''

def print_many2many(entity, fval, user):
    output = []

    if issubclass(fval.model, CremeEntity):
        entities = list(fval.filter(is_deleted=False))
        #CremeEntity.populate_credentials(entities, user)
        output.extend('<li>%s</li>' % (e.get_entity_m2m_summary(user) if e.can_view(user) else
                                       e.allowed_unicode(user)
                                      ) for e in entities
                     )
    else:
        output.extend('<li>%s</li>' % escape(a) for a in fval.all())

    if output:
        output = chain(['<ul>'], output, ['</ul>'])

    return ''.join(output)

def print_duration(entity, fval, user):
    try:
        h, m, s = fval.split(':')
    except (ValueError, AttributeError):
        return ''

    h = int(h)
    m = int(m)
    s = int(s)

    return '%(hour)s %(hour_label)s %(minute)s %(minute_label)s %(second)s %(second_label)s' % {
        'hour': h,
        'hour_label': ungettext('hour', 'hours', h),
        'minute': m,
        'minute_label': ungettext('minute', 'minutes', m),
        'second': s,
        'second_label': ungettext('second', 'seconds', s)
    }

#TODO: Do more specific fields (i.e: currency field....) ?
class _FieldPrintersRegistry(object):
    def __init__(self):
        self._printers = {
            models.AutoField:                  simple_print,
            models.BooleanField:               lambda entity, fval, user: '<input type="checkbox" value="%s" %s disabled/>%s' % (escape(fval), 'checked' if fval else '', _('Yes') if fval else _('No')),
            models.CharField:                  simple_print,
            models.CommaSeparatedIntegerField: simple_print,
            models.DateField:                  print_date,
            models.DateTimeField:              print_datetime,
            models.DecimalField:               simple_print,
            models.EmailField:                 lambda entity, fval, user: '<a href="mailto:%s">%s</a>' % (fval, fval) if fval else '',
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
            models.TextField:                  lambda entity, fval, user: linebreaks(fval) if fval else "",
            models.TimeField:                  simple_print,
            models.URLField:                   print_urlfield,
            models.ForeignKey:                 print_foreignkey,
            models.ManyToManyField:            print_many2many,
            models.OneToOneField:              print_foreignkey,

            fields.PhoneField:                 simple_print,
            fields.DurationField:              print_duration,
            fields.ModificationDateTimeField:  print_datetime,
            fields.CreationDateTimeField :     print_datetime,
        }

    def register(self, field, printer):
        """Register a field printer.
        @param field A class inheriting django.models.Field
        @param printer A callable with 2 parameter: 'obj' & 'fval'. See simple_print, print_urlfield etc...
        """
        self._printers[field] = printer

    def get_html_field_value(self, obj, field_name, user):
        field_class, field_value = get_instance_field_info(obj, field_name)

        if field_class is None:
            fields_through = [f['field'].__class__ for f in get_model_field_info(obj.__class__, field_name)]

            if models.ManyToManyField in fields_through: #TODO: use any() instead
                return get_m2m_entities(obj, field_name, get_value=True,
                                        get_value_func=(lambda values: ", ".join([val for val in values if val])),  #TODO: use (i)filter
                                        user=user
                                       )

        print_func = self._printers.get(field_class)

        if print_func:
            return mark_safe(print_func(obj, field_value, user))

        return field_value


field_printers_registry = _FieldPrintersRegistry()
