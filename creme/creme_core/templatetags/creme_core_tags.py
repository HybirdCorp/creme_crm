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

from time import mktime
from re import compile as compile_re
from logging import debug

from django import template
from django.contrib.contenttypes.models import ContentType

from creme_core.gui.field_printers import field_printers_registry
from creme_core.utils.meta import get_verbose_field_name


register = template.Library()

@register.filter(name="print_boolean") #TODO: factorise with field_printers ?
def print_boolean(x):
    return mark_safe('<input type="checkbox" value="%s" %s disabled/>' % (escape(x), 'checked' if x else ''))#Potentially double safe marked

@register.filter(name="get_html_field_value")
def get_html_field_value(obj, field_name):
    return field_printers_registry.get_html_field_value(obj, field_name)

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
  except Exception, e: #TODO: really useful ???
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

@register.simple_tag
def get_field_verbose_name(model_or_entity, field_name):
    return get_verbose_field_name(model_or_entity, field_name) or field_name

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

@register.filter(name="and_op")
def and_op(object1, object2):
    return bool(object1 and object2)

@register.filter(name="str")
def _str(object1):
    return str(object1)

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

    def __repr__(self):
        return "<Templatize node>"

    def render(self, context):
        context[self.var_name] = self.inner_template.render(context)
        return ''

#TODO: move to a 'creme_auth' file ??
_haspermto_re = compile_re(r'(\w+) (.*?) as (\w+)')

def _can_create(model_or_ct, user):
    ct = model_or_ct if isinstance(model_or_ct, ContentType) else ContentType.objects.get_for_model(model_or_ct)

    return user.has_perm('%s.add_%s' % (ct.app_label, ct.model))

_PERMS_FUNCS = {
        'create': _can_create,
        'view':   lambda entity, user: entity.can_view(user),
        'change': lambda entity, user: entity.can_change(user),
        'delete': lambda entity, user: entity.can_delete(user),
        'link':   lambda entity, user: entity.can_link(user),
        'unlink': lambda entity, user: entity.can_unlink(user),
    }

@register.tag(name="has_perm_to")
def do_has_perm_to(parser, token):
    """{% has_perm_to TYPE OBJECT as VAR %}
    eg: {% has_perm_to change action.creme_entity as has_perm %}

    TYPE: in ('create', 'view','change', 'delete', 'link', 'unlink')
    OBJECT: must be a CremeEntity, for ('view','change', 'delete', 'link', 'unlink') types
            and a class inheriting from CremeEntity OR a ContentType instance for 'create' type.
    """
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _haspermto_re.search(arg)
    if not match:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments: %r" % (tag_name, arg)

    perm_type, entity_path, var_name = match.groups()

    perm_func = _PERMS_FUNCS.get(perm_type)
    if not perm_func:
        raise template.TemplateSyntaxError, "%r invalid permission tag: %r" % (tag_name, perm_type)

    #TODO: don't attack defaulttags but parser api ??
    entity_var = template.defaulttags.TemplateLiteral(parser.compile_filter(entity_path), entity_path)

    return HasPermToNode(perm_func, entity_var, var_name)

class HasPermToNode(template.Node):
    def __init__(self, perm_func, entity_var, var_name):
        self.perm_func = perm_func
        self.entity_var = entity_var
        self.var_name = var_name

    def __repr__(self):
        return "<HasPermTo node>"

    def render(self, context):
        var  = self.entity_var.eval(context) #can raise template.VariableDoesNotExist...
        user = context['request'].user #TODO: context['user'] ???

        context[self.var_name] = self.perm_func(var, user)

        return ''

@register.filter(name="allowed_unicode")
def allowed_unicode(entity, user):
    return entity.allowed_unicode(user)
