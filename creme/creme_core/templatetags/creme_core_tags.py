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

import logging
#from time import mktime
from re import compile as compile_re

#from django import template
from django.template import Library, Template, TemplateSyntaxError, Node as TemplateNode # Token
from django.template.defaulttags import TemplateLiteral
#from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import dumps
from django.contrib.contenttypes.models import ContentType

#from mediagenerator.templatetags.media import include_media
from mediagenerator.generators.bundles.utils import _render_include_media

from ..gui.field_printers import field_printers_registry
from ..models import CremeEntity, Relation
from ..utils.currency_format import currency
from ..utils.media import get_creme_media_url, get_current_theme
from ..utils.meta import get_verbose_field_name
from ..registry import export_backend_registry, import_backend_registry


logger = logging.getLogger(__name__)
register = Library()


@register.filter(name="print_boolean") #TODO: factorise with field_printers ?
def print_boolean(x):
    if isinstance(x, bool):
        return mark_safe('<input type="checkbox" value="%s" %s disabled/>%s' % (
                                x, #escape(x),
                                'checked' if x else '',
                                _('Yes') if x else _('No')
                            )
                        ) #Potentially double safe marked

    return x

@register.filter
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
    logger.debug('Exception in get_value(): %s', e)
    return default

@register.filter
def get_meta_value(obj, key, default=''):
    try:
        return getattr(obj._meta, key)
    except:
        return default

#@register.filter(name="get_list_object_of_specific_relations")
#def get_related_entities(entity, relation_type_id):
    #return entity.get_related_entities(relation_type_id)

#@register.filter
#def get_extra_field_value(object, field_name):
    #return object.__getattribute__(field_name)() #todo: use getattr() ??

@register.filter(name="get_tag")
def get_fieldtag(field, tag):
    """eg: {% if field|get_tag:'viewable' %}"""
    return field.get_tag(tag)

@register.simple_tag
def get_field_verbose_name(model_or_entity, field_name):
    return get_verbose_field_name(model_or_entity, field_name) or field_name

#@register.filter
#def is_date_gte(date1, date2):
    #return date1.replace(hour=0, minute=0, second=0, microsecond=0) >= date2.replace(hour=0, minute=0, second=0, microsecond=0)

#@register.filter
#def is_date_lte(date1, date2):
    #return date1.replace(hour=0, minute=0, second=0, microsecond=0) <= date2.replace(hour=0, minute=0, second=0, microsecond=0)

@register.filter
def is_entity(obj):
    return isinstance(obj, CremeEntity)

@register.filter
def is_relation(obj):
    return isinstance(obj, Relation)

#@register.filter
#def in_day(date1, day_in):
    #beg = day_in.replace(hour=0, minute=0, second=0, microsecond=0)
    #end = day_in.replace(hour=23, minute=59, second=59, microsecond=999999)
    #return is_date_gte(date1, beg) and is_date_lte(date1, end)

#@register.filter
#def range_timestamp(date1, date2):
    #return abs(mktime(date2.timetuple()) - mktime(date1.timetuple()))

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

@register.filter
def sub(object1, object2):
    return object1 - object2

@register.filter
def and_op(object1, object2):
    return bool(object1 and object2)

@register.filter(name="str")
def _str(object1):
    return str(object1)

#NB: 'abs' name gives a template syntax error
@register.filter
def absolute(integer):
    return abs(integer)

@register.filter(name="in")
def in_list(obj, list):
   return obj in list

@register.filter
def idiv(integer, integer2):
    return integer / integer2

@register.filter
def mult(integer, integer2):
    return integer * integer2

#TODO: divisibleby in builtins....
@register.filter
def mod(integer, integer2):
    return integer % integer2

@register.filter(name="xrange")
def x_range(integer, start=0):
    return xrange(start, start + integer)

@register.filter
def isiterable(iterable):
    return hasattr(iterable, '__iter__')

@register.filter(name="format")
def format_string(ustring, format_str):
    return format_str % ustring

@register.filter(name="enumerate") #TODO: why not use forloop.counter/counter0
def enumerate_iterable(iterable):
    return enumerate(iterable)

@register.filter
def to_timestamp(date):
    return date.strftime('%s')

@register.filter
def allowed_unicode(entity, user):
    return entity.allowed_unicode(user)

@register.filter
def format_amount(amount, currency_id):
    return currency(amount, currency_id)

@register.simple_tag
def get_entity_summary(entity, user):
    return entity.get_entity_summary(user)


#TAG : "templatize"-------------------------------------------------------------
_templatize_re = compile_re(r'(.*?) as (\w+)')

@register.tag(name="templatize")
def do_templatize(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _templatize_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments: %r" % (tag_name, arg)

    template_string, var_name = match.groups()

    first_char = template_string[0]
    if not (first_char == template_string[-1] and first_char in ('"', "'")):
        raise TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

    return TemplatizeNode(template_string[1:-1], var_name)

class TemplatizeNode(TemplateNode):
    def __init__(self, template_string, var_name):
        self.inner_template = Template(template_string)
        self.var_name = var_name

    def __repr__(self):
        return "<Templatize node>"

    def render(self, context):
        context[self.var_name] = self.inner_template.render(context)
        return ''

#TAG : "print_field"------------------------------------------------------------
_PRINT_FIELD_RE = compile_re(r'object=(.*?) field=(.*?)$')

@register.tag(name="print_field")
def do_print_field(parser, token):
    """Eg:{% print_field object=object field='created' %}"""
    try:
        tag_name, arg = token.contents.split(None, 1) # Splitting by None == splitting by spaces.
    except ValueError:
        raise TemplateSyntaxError("%r tag requires arguments" % token.contents.split()[0])

    match = _PRINT_FIELD_RE.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments" % tag_name

    obj_str, field_str = match.groups()
    compile_filter = parser.compile_filter

    return FieldPrinterNode(obj_var=TemplateLiteral(compile_filter(obj_str), obj_str),
                            field_var=TemplateLiteral(compile_filter(field_str), field_str)
                           )

class FieldPrinterNode(TemplateNode):
    def __init__(self, obj_var, field_var):
        self.obj_var = obj_var
        self.field_var = field_var

    def render(self, context):
        obj        = self.obj_var.eval(context)
        field_name = self.field_var.eval(context)

        return field_printers_registry.get_html_field_value(obj, field_name, context['user'])

#TAG : "has_perm_to"------------------------------------------------------------

#TODO: move to a 'creme_auth' file ??
_haspermto_re = compile_re(r'(\w+) (.*?) as (\w+)')

def _can_create(model_or_ct, user):
    ct = model_or_ct if isinstance(model_or_ct, ContentType) else ContentType.objects.get_for_model(model_or_ct)
    return user.has_perm('%s.add_%s' % (ct.app_label, ct.model))

def _can_export(model_or_ct, user):
    ct = model_or_ct if isinstance(model_or_ct, ContentType) else ContentType.objects.get_for_model(model_or_ct)
    return user.has_perm('%s.export_%s' % (ct.app_label, ct.model))

_PERMS_FUNCS = {
        'create': _can_create,
        'export': _can_export,
        'view':   lambda entity, user: user.has_perm_to_view(entity),
        'change': lambda entity, user: user.has_perm_to_change(entity),
        'delete': lambda entity, user: user.has_perm_to_delete(entity),
        'link':   lambda entity_or_model, user: user.has_perm_to_link(entity_or_model),
        'unlink': lambda entity, user: user.has_perm_to_unlink(entity),
    }

@register.tag(name="has_perm_to")
def do_has_perm_to(parser, token):
    """{% has_perm_to TYPE OBJECT as VAR %}
    eg: {% has_perm_to change action.creme_entity as has_perm %}

    TYPE: miust be in ('create', 'view','change', 'delete', 'link', 'unlink', 'create', 'export')
    OBJECT: * TYPE in ('view','change', 'delete', 'unlink') => must be a CremeEntity.
            * TYPE='link' => can be a CremeEntity instance or a class inheriting from CremeEntity.
            * TYPE in ('create', 'export') and a class inheriting from CremeEntity OR a ContentType instance.
    """
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = _haspermto_re.search(arg)
    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments: %r" % (tag_name, arg)

    perm_type, entity_path, var_name = match.groups()

    perm_func = _PERMS_FUNCS.get(perm_type)
    if not perm_func:
        raise TemplateSyntaxError, "%r invalid permission tag: %r" % (tag_name, perm_type)

    entity_var = TemplateLiteral(parser.compile_filter(entity_path), entity_path)

    return HasPermToNode(perm_func, entity_var, var_name)

class HasPermToNode(TemplateNode):
    def __init__(self, perm_func, entity_var, var_name):
        self.perm_func = perm_func
        self.entity_var = entity_var
        self.var_name = var_name

    def __repr__(self):
        return "<HasPermTo node>"

    def render(self, context):
        var  = self.entity_var.eval(context) #can raise template.VariableDoesNotExist...
        user = context['user']
        context[self.var_name] = self.perm_func(var, user)

        return ''

@register.simple_tag(takes_context=True)
def creme_media_url(context, url):
    return get_creme_media_url(context.get('THEME_NAME', 'chantilly'), url)

#@register.tag
#def include_creme_media(parser, token):
    #contents = token.split_contents()
    #contents[1] = u'"%s%s"' % (get_current_theme(), contents[1][1:-1])
    #return include_media(parser, Token(token.token_type, ' '.join(contents)))

@register.tag(name='include_creme_media')
def do_include_creme_media(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    return MediaNode(TemplateLiteral(parser.compile_filter(arg), arg))

class MediaNode(TemplateNode):
    def __init__(self, bundle_var):
        self.bundle_var = bundle_var

    def render(self, context):
        bundle = self.bundle_var.eval(context)

        return _render_include_media(get_current_theme() + bundle, variation={})

@register.assignment_tag
def get_export_backends():
    return dumps([[backend.id, unicode(backend.verbose_name)]
                 for backend in export_backend_registry.iterbackends()])

@register.assignment_tag
def get_import_backends():
    return dumps([[backend.id] for backend in import_backend_registry.iterbackends()])
