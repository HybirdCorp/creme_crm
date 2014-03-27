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

from itertools import chain

from django.conf import settings
from django.db import models
from django.template.defaultfilters import linebreaks
from django.utils.formats import date_format
from django.utils.html import escape
#from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import ungettext, ugettext_lazy as _

from ..models import CremeEntity, fields
from ..utils.meta import FieldInfo #get_model_field_info
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

def simple_print_csv(entity, fval, user):
    return unicode(fval) if fval is not None else ""

def print_image(entity, fval, user):
    return """<a onclick="creme.dialogs.image('%(url)s').open();"><img src="%(url)s" %(size)s alt="%(url)s"/></a>""" % {
                'url':  fval.url,
                'size': image_size(fval),
            }

def print_boolean(entity, fval, user):
    if fval:
        checked = 'checked '
        label = _('Yes')
    else:
        checked = ''
        label = _('No')

    return u'<input type="checkbox" value="%s" %sdisabled/>%s' % (
                escape(fval), checked, label
            )

def print_urlfield(entity, fval, user):
    if not fval:
        return ""

    esc_fval = escape(fval)
    return '<a href="%s" target="_blank">%s</a>' % (esc_fval, esc_fval)

def print_datetime(entity, fval, user):
    #return date_format(fval, 'DATETIME_FORMAT') if fval else ''
    return date_format(localtime(fval), 'DATETIME_FORMAT') if fval else ''

def print_date(entity, fval, user):
    return date_format(fval, 'DATE_FORMAT') if fval else ''

def print_foreignkey(entity, fval, user):
    #TODO: temporary hack before print_field refactor in order to give extra parameters for custom display. 
    from creme.media_managers.models.image import Image

    if isinstance(fval, Image) and user.has_perm_to_view(fval):
        return u'<a onclick="creme.dialogs.image(\'%s\').open();"%s>%s</a>' % (
                fval.get_image_url(),
                ' class="is_deleted"' if fval.is_deleted else u'',
                fval.get_entity_summary(user)
            )

    if isinstance(fval, CremeEntity):
        return widget_entity_hyperlink(fval, user)

    return unicode(fval) if fval else u''

def print_foreignkey_csv(entity, fval, user):
    if isinstance(fval, CremeEntity):
        #TODO: change allowed unicode ??
        return unicode(fval) if user.has_perm_to_view(fval) else settings.HIDDEN_VALUE

    return unicode(fval) if fval else u''

def print_many2many(entity, fval, user):
    output = []

    #TODO: temporary hack before print_field refactor in order to give extra parameters for custom display. 
    from creme.media_managers.models.image import Image

    def print_entity_link(e):
        if not user.has_perm_to_view(e):
            return settings.HIDDEN_VALUE

        if isinstance(e, Image):
            return u'<a onclick="creme.dialogs.image(\'%s\').open();"%s>%s</a>' % (e.get_image_url(),
                                                                                   ' class="is_deleted"' if e.is_deleted else u'',
                                                                                   e.get_entity_summary(user)
                                                                                  )

        return u'<a target="_blank" href="%s"%s>%s</a>' % (e.get_absolute_url(),
                                                           ' class="is_deleted"' if e.is_deleted else u'',
                                                           e.get_entity_summary(user))

    if issubclass(fval.model, CremeEntity):
        output.extend('<li>%s</li>' % print_entity_link(e) for e in fval.filter(is_deleted=False))
    else:
        output.extend('<li>%s</li>' % escape(a) for a in fval.all())

    if output:
        output = chain(['<ul>'], output, ['</ul>'])

    return ''.join(output)

def print_many2many_csv(entity, fval, user):
    if issubclass(fval.model, CremeEntity):
        #TODO: CSV summary ?? [e.get_entity_m2m_summary(user)]
        return u'/'.join(unicode(e) if user.has_perm_to_view(e)
                         else settings.HIDDEN_VALUE
                            for e in fval.filter(is_deleted=False)
                        )

    return u'/'.join(unicode(a) for a in fval.all())

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
            #models.AutoField:                  simple_print,
            models.BooleanField:               print_boolean,
            #models.CharField:                  simple_print,
            #models.CommaSeparatedIntegerField: simple_print,
            models.DateField:                  print_date,
            models.DateTimeField:              print_datetime,
            #models.DecimalField:               simple_print,
            models.EmailField:                 lambda entity, fval, user: '<a href="mailto:%s">%s</a>' % (fval, fval) if fval else '',
            #models.FileField:                  simple_print,
            #models.FilePathField:              simple_print,
            #models.FloatField:                 simple_print,
            models.ImageField:                 print_image,
            #models.IntegerField:               simple_print,
            #models.IPAddressField:             simple_print,
            #models.NullBooleanField:           simple_print,
            #models.PositiveIntegerField:       simple_print,
            #models.PositiveSmallIntegerField:  simple_print,
            #models.SlugField:                  simple_print,
            #models.SmallIntegerField:          simple_print,
            models.TextField:                  lambda entity, fval, user: linebreaks(fval) if fval else "",
            #models.TimeField:                  simple_print,
            models.URLField:                   print_urlfield,
            models.ForeignKey:                 print_foreignkey,
            models.ManyToManyField:            print_many2many,
            models.OneToOneField:              print_foreignkey,

            #fields.PhoneField:                 simple_print,
            fields.DurationField:              print_duration,

            fields.ModificationDateTimeField:  print_datetime, #TODO: use inheritance, & remove this line ??
            fields.CreationDateTimeField :     print_datetime,
        }
        self._csv_printers = {
            models.BooleanField:               lambda entity, fval, user: _('Yes') if fval else _('No'),
            models.DateField:                  print_date,
            models.DateTimeField:              print_datetime,
            #models.ImageField:                 print_image, TODO ??

            models.ForeignKey:                 print_foreignkey_csv,
            models.ManyToManyField:            print_many2many_csv,
            models.OneToOneField:              print_foreignkey_csv,

            fields.DurationField:              print_duration,

            fields.ModificationDateTimeField:  print_datetime,
            fields.CreationDateTimeField :     print_datetime,
        }
        self._printers_maps = {
                'html': (self._printers,     simple_print),
                'csv':  (self._csv_printers, simple_print_csv),
            }

        self.css_default_listview = css_default_listview = getattr(settings, 'CSS_DEFAULT_LISTVIEW')
        self.css_default_header_listview = css_default_header_listview = getattr(settings, 'CSS_DEFAULT_HEADER_LISTVIEW')

        css_number_listview = getattr(settings, 'CSS_NUMBER_LISTVIEW', css_default_listview)
        css_textarea_listview = getattr(settings, 'CSS_TEXTAREA_LISTVIEW', css_default_listview)
        css_date_header_listview = getattr(settings, 'CSS_DATE_HEADER_LISTVIEW', css_default_header_listview)

        self._listview_css_printers = {
            models.CommaSeparatedIntegerField: css_number_listview,
            models.DecimalField:               css_number_listview,
            models.FloatField:                 css_number_listview,
            models.PositiveIntegerField:       css_number_listview,
            models.PositiveSmallIntegerField:  css_number_listview,
            models.TextField:                  css_textarea_listview,
        }

        self._header_listview_css_printers = {
            models.DateField:                   css_date_header_listview,
            fields.CreationDateTimeField:       css_date_header_listview,
            fields.ModificationDateTimeField:   css_date_header_listview,
            models.DateTimeField:               css_date_header_listview,
        }

    def register(self, field, printer):
        """Register a field printer.
        @param field A class inheriting django.models.Field
        @param printer A callable with 2 parameter: 'obj' & 'fval'. See simple_print, print_urlfield etc...
        """
        self._printers[field] = printer

    def register_listview_css_class(self, field, css_class, header_css_class):
        """Register a listview css class for field .
        @param field A class inheriting django.models.Field
        @param css_class A string
        """
        self._listview_css_printers[field] = css_class
        self._header_listview_css_printers[field] = header_css_class

    def get_listview_css_class_for_field(self, field_class):
        return self._listview_css_printers.get(field_class, self.css_default_listview)

    def get_header_listview_css_class_for_field(self, field_class):
        return self._header_listview_css_printers.get(field_class, self.css_default_header_listview)

    def _build_field_printer(self, field_info, output='html'):
        base_field = field_info[0]
        base_name = base_field.name
        HIDDEN_VALUE = settings.HIDDEN_VALUE

        if len(field_info) > 1:
            base_model = base_field.rel.to
            sub_printer = self._build_field_printer(field_info[1:], output)

            if isinstance(base_field, models.ForeignKey):
                if issubclass(base_model, CremeEntity):
                    def printer(obj, user):
                        base_value = getattr(obj, base_name)

                        if base_value is None:
                            return ''

                        if not user.has_perm_to_view(base_value):
                            return HIDDEN_VALUE

                        return sub_printer(base_value, user)
                else:
                    def printer(obj, user):
                        base_value = getattr(obj, base_name)

                        if base_value is None:
                            return ''

                        return sub_printer(base_value, user)
            else:
                assert isinstance(base_field, models.ManyToManyField)

                if issubclass(base_model, CremeEntity):
                    if output == 'csv':
                        def printer(obj, user):
                            has_perm = user.has_perm_to_view

                            return u'/'.join(sub_printer(e, user) if has_perm(e) else HIDDEN_VALUE
                                                for e in getattr(obj, base_name).filter(is_deleted=False)
                                            )
                    else:
                        def printer(obj, user):
                            has_perm = user.has_perm_to_view
                            lines = ['<li>%s</li>' % (
                                            sub_printer(e, user) if has_perm(e)
                                            else HIDDEN_VALUE
                                        ) for e in getattr(obj, base_name).filter(is_deleted=False)
                                    ]

                            if lines:
                                lines = chain(('<ul>',), lines, ('</ul>',))

                            return ''.join(lines)
                else:
                    if output == 'csv':
                        def printer(obj, user):
                            return u'/'.join(sub_printer(a, user)
                                                for a in getattr(obj, base_name).all()
                                            )
                    else:
                        def printer(obj, user):
                            lines = ['<li>%s</li>' % sub_printer(a, user)
                                        for a in getattr(obj, base_name).all()
                                    ]

                            if lines:
                                lines = chain(('<ul>',), lines, ('</ul>',))

                            return ''.join(lines)
        else:
            printer_funcs, default_func = self._printers_maps[output]
            print_func = printer_funcs.get(base_field.__class__, default_func)

            def printer(obj, user):
                #return mark_safe(print_func(obj, getattr(obj, base_name), user))
                return print_func(obj, getattr(obj, base_name), user)

        return printer

    def build_field_printer(self, model, field_name, output='html'):
        return self._build_field_printer(FieldInfo(model, field_name), output=output)

    def get_html_field_value(self, obj, field_name, user):
        return self.build_field_printer(obj.__class__, field_name)(obj, user)

    def get_csv_field_value(self, obj, field_name, user):
        return self.build_field_printer(obj.__class__, field_name, output='csv')(obj, user)


field_printers_registry = _FieldPrintersRegistry()
