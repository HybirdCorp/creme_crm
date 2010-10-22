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

from time import mktime
from re import compile as compile_re
from logging import debug

from django.db import models
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

from creme_core.models import CremeEntity
from creme_core.models import fields
from creme_core.utils.meta import get_field_infos, get_model_field_infos, get_m2m_entities

from media_managers.models import Image


register = template.Library()

def get_foreign_key_popup_str(x):
    if hasattr(x, 'get_absolute_url') and hasattr(x, 'entity_type'):
        return '<a href="%s"><u>%s</u></a>' % (x.get_absolute_url(), x)
    return '%s' % x if x else ''

####

IMAGES_ATTRIBUTES = {Image: 'image'}

def get_m2m_popup_str(x):
    result   = '<ul>'
    img_attr = IMAGES_ATTRIBUTES.get(x.model)

    if img_attr is not None:
        for a in x.all():
            esc_a = escape(a)
            result += '<li><img src="%s" alt="%s" title="%s" %s class="magnify"/></li>' % \
                      (a.__getattribute__(img_attr).url, esc_a, esc_a, image_size(a, 80, 80))
    else:
        for a in x.all():
            if hasattr(a, 'get_absolute_url'):
                result += '<li><a target="_blank" href="%s">%s</li></a>' % (a.get_absolute_url(), escape(a))
            else:
                result += '<li>%s</li>' % escape(a)
    result += '</ul>'
    return result

####

MAX_HEIGHT = 200
MAX_WIDTH = 200

@register.filter(name="get_html_image_size") 
def image_size(image, max_h=MAX_HEIGHT, max_w=MAX_WIDTH):
    debug('image_size')

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
####

def simple_print(x):
    return '%s' % escape(x) if x is not None else ""

def print_imagefield(x):
    url = x.url
    return """<a href="javascript:openWindow('%s','image_popup');"><img src="%s" %s alt="%s"/></a>""" % \
            (url, url, image_size(x), url)

def print_urlfield(x):
    esc_x = escape(x)
    return '<a href="%s" target="_blank">%s</a>' % (esc_x, esc_x)

#TODO: remove all avlue with simple_print => classes.get(KEY, simple_print) ??
classes = {
     models.AutoField:                  simple_print,
     models.BooleanField:               lambda x: '<input type="checkbox" value="%s" %s disabled/>' % (escape(x), 'checked' if x else ''),
     models.CharField:                  simple_print,
     models.CommaSeparatedIntegerField: simple_print,
     models.DateField:                  lambda x: x.strftime('%d/%m/%Y') if x else '',
     models.DateTimeField:              lambda x: x.strftime('%d/%m/%Y %H:%M') if x else '',
#     models.DateTimeField:              simple_print,
     models.DecimalField:               simple_print,
     models.EmailField:                 simple_print,
     models.FileField:                  simple_print,
     models.FilePathField:              simple_print,
     models.FloatField:                 simple_print,
     models.ImageField:                 print_imagefield,
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

     fields.ModificationDateTimeField:  simple_print,
     fields.CreationDateTimeField :     simple_print,
     #fields.AutoSlugField:              simple_print,
}

@register.filter(name="get_html_field_value")
def get_html_field_value(obj, field_name):
    field_class, field_value = get_field_infos(obj, field_name)

    if field_class is None:
        fields_through = [f['field'].__class__ for f in get_model_field_infos(obj.__class__, field_name)]
        if models.ManyToManyField in fields_through:
            return get_m2m_entities(obj, field_name, get_value=True, get_value_func=lambda values: ", ".join([val for val in values if val]))

    print_func = classes.get(field_class)
    if print_func is not None:
        return mark_safe(print_func(field_value))
    return field_value

@register.filter(name="get_value")
def get_value(dic, key, default=''):
  """
  Usage: 

  view: 
  some_dict = {'keyA':'valueA','keyB':{'subKeyA':'subValueA','subKeyB':'subKeyB'},'keyC':'valueC'}
  keys = ['keyA','keyC']
  template: 
  {{ some_dict|get:"keyA" }}
  {{ some_dict|get:"keyB"|get:"subKeyA" }}
  {% for key in keys %}{{ some_dict|get:key }}{% endfor %}
  """
  try:
    return dic.get(key, default)
  except Exception, e: ##USEFUL ???
    debug('Exception in get_value(): %s', e)
    return default

@register.filter(name="get_meta_value")
def get_meta_value(obj, key, default=''):
    try:
        return getattr(obj._meta, key)
    except:
        return default

@register.filter(name="get_list_object_of_specific_relations") #TODO: rename tag ?
def get_related_entities(entity, relation_type_id):
    return entity.get_related_entities(relation_type_id)

@register.filter(name="get_extra_field_value")
def get_extra_field_value(object, field_name):
    return object.__getattribute__(field_name)() #TODO: use getattr() ??

@register.filter(name="is_date_gte")
def is_date_gte(date1, date2):
    return date1.replace(hour=0, minute=0, second=0, microsecond=0) >= date2.replace(hour=0, minute=0, second=0, microsecond=0)

@register.filter(name="is_date_lte")
def is_date_lte(date1, date2):
    return date1.replace(hour=0, minute=0, second=0, microsecond=0) <= date2.replace(hour=0, minute=0, second=0, microsecond=0)

@register.filter(name="in_day")
def in_day(date1, day_in):
    beg = day_in.replace(hour=0, minute=0, second=0, microsecond=0)
    end = day_in.replace(hour=23, minute=59, second=59, microsecond=999999)
    return is_date_gte(date1, beg) and is_date_lte(date1, end)

@register.filter(name="range_timestamp")
def range_timestamp(date1, date2):
    return abs(mktime(date2.timetuple()) - mktime(date1.timetuple()))

#@register.filter(name="lt")
#def lt(object1, object2):
    #return object1 < object2

#@register.filter(name="gt")
#def gt(object1, object2):
    #return object1 > object2

#@register.filter(name="lte")
#def lte(object1, object2):
    #return object1 <= object2

#@register.filter(name="gte")
#def gte(object1, object2):
    #return object1 >= object2

#@register.filter(name="eq")
#def eq(object1, object2):
    #return object1 == object2

@register.filter(name="sub")
def sub(object1, object2):
    return object1 - object2

# TODO : abs name gives a template syntax error
@register.filter(name="absolute")
def absolute(integer):
    return abs(integer)

#@register.filter(name="in")
#def in_list(obj, list):
   #return obj in list

@register.filter(name="idiv")
def idiv(integer, integer2):
    return integer / integer2

@register.filter(name="mult")
def mult(integer, integer2):
    return integer * integer2

#TODO: divisibleby in builtins....
@register.filter(name="mod")
def mod(integer, integer2):
    return integer % integer2

@register.filter(name="xrange")
def x_range(integer, start=0):
    return xrange(start, start + integer)

@register.filter(name="isiterable")
def isiterable(iterable):
    return hasattr(iterable, '__iter__')

@register.filter(name="format")
def format(ustring, format_str):
    return format_str % ustring

@register.filter(name="enumerate")
def enumerate_iterable(iterable):
    return enumerate(iterable)

@register.filter(name="to_timestamp")
def to_timestamp(date):
    return date.strftime('%s')

_templatize_re = compile_re(r'(.*?) as (\w+)')

@register.tag(name="templatize")
def do_templatize(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _templatize_re.search(arg)
    if not match:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments: %r" % (tag_name, arg)

    template_string, var_name = match.groups()

    first_char = template_string[0]
    if not (first_char == template_string[-1] and first_char in ('"', "'")):
        raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    return TemplatizeNode(template_string[1:-1], var_name)

class TemplatizeNode(template.Node):
    def __init__(self, template_string, var_name):
        self.inner_template = template.Template(template_string)
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = self.inner_template.render(context)
        return ''
