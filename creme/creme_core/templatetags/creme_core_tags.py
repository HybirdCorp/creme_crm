################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import warnings
from itertools import zip_longest
from re import compile as compile_re
from urllib.parse import urlencode, urlsplit

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template import Library
from django.template import Node as TemplateNode
from django.template import Template, TemplateSyntaxError
from django.template.defaulttags import TemplateLiteral
from django.template.library import token_kwargs
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import escape, format_html_join
from django.utils.safestring import mark_safe

from mediagenerator.generators.bundles.utils import _render_include_media

from ..core.entity_cell import EntityCell
from ..gui.bulk_update import bulk_update_registry
from ..gui.field_printers import field_printers_registry
from ..gui.view_tag import ViewTag
from ..http import is_ajax
from ..models import CremeEntity, Relation
from ..utils import bool_as_html
from ..utils.currency_format import currency
from ..utils.html import escapejson
from ..utils.serializers import json_encode
from ..utils.translation import plural
from ..utils.unicode_collation import collator

logger = logging.getLogger(__name__)
register = Library()


@register.filter
def app_verbose_name(app_label, default='?'):
    """Get the verbose name of a django app, from its label."""
    get_app = apps.get_app_config

    try:
        app = get_app(app_label)
    except LookupError:
        logger.warning('The app "%s" seems not registered.', app_label)
        return default

    return app.verbose_name


@register.filter(name='print_boolean')
def print_boolean(x):
    """Represent a boolean value as an HTML check-box with a label."""
    return bool_as_html(x)


@register.filter
def get_by_index(sequence, index):
    """Get the Nth item in a sequence (index can be a context variable).

    Usage:
        Context:
            {
                'my_list': ['a', 'b', 'c'],
                'my_idx': 1,
            }

        Template file:
          {{my_list|get_by_index:my_idx}}{# Displays 'b' #}
    """
    return sequence[index]


@register.filter
def get_value(dic, key, default=''):
    """Get a value from its key in a dictionary-like object.
    A default value is used as fallback (like <dict.get()>).

    Usage:
        Context:
            {
                'some_dict': {
                  'keyA': 'valueA',
                  'keyB': {'subKeyA': 'subValueA', 'subKeyB': 'subKeyB'},
                  'keyC': 'valueC',
                },
                'keys': ['keyA','keyC'],
            }

        Template file:
            {{ some_dict|get_value:"keyA" }}
            {{ some_dict|get_value:"keyB"|get_value:"subKeyA" }}
            {% for key in keys %}{{ some_dict|get_value:key }}{% endfor %}
    """
    try:
        return dic.get(key, default)
    except Exception as e:  # TODO: really useful ???
        logger.debug('Exception in get_value(): %s', e)
        return default


@register.filter
def get_meta_value(obj, key, default=''):
    """Get the value of a Meta attribute for a 'django.db.models.Model' instance."""
    try:
        return getattr(obj._meta, key)
    except AttributeError as e:
        logger.warning('Templatetag get_meta_value: %s', e)

    return default


_log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR':    logging.ERROR,
    'WARN':     logging.WARNING,
    'INFO':     logging.INFO,
    'DEBUG':    logging.DEBUG,
}


@register.simple_tag
def log(msg, level='INFO'):
    """Log a string using the logging system.
    It's useful to indicate that a template file is deprecated for example.
    """
    logger.log(_log_levels.get(level, logging.INFO), msg)
    return ''


# TODO: 'o|is_op:None' instead ?
@register.filter
def is_none(obj):
    return obj is None


# TODO: replace by a filter 'ctype_is' in creme_ctype.py ?
@register.filter
def is_entity(obj):
    return isinstance(obj, CremeEntity)


@register.filter
def is_relation(obj):
    return isinstance(obj, Relation)


@register.filter(name='lt')
def lt(x, y):
    """<Lesser than> operator."""
    return x < y


@register.filter(name='gt')
def gt(x, y):
    """<Greater than> operator."""
    return x > y


@register.filter(name='lte')
def lte(x, y):
    """<Lesser or equal> operator."""
    return x <= y


@register.filter(name='gte')
def gte(x, y):
    """<Greater or equal> operator."""
    return x >= y


@register.filter(name='eq')
def eq(x, y):
    """<Equal> operator."""
    return x == y


@register.filter
def and_op(object1, object2):
    """<and> operator."""
    return object1 and object2


@register.filter
def or_op(object1, object2):
    """<or> operator."""
    return object1 or object2


@register.filter
def not_op(obj):
    """<not> operator."""
    return not obj


@register.filter(name='bool')
def _bool(object1):
    """Cast an object to a boolean."""
    return bool(object1)


# NB: shortcut for stringformat:'s'
@register.filter(name='str')
def _str(object1):
    """Cast an object to a string."""
    return str(object1)


# NB: 'abs' name gives a template syntax error
@register.filter
def absolute(integer):
    """Get the absolute value of a number."""
    return abs(integer)


@register.filter(name='in')
def in_list(obj, sequence):
    """Is a value contained by a sequence."""
    return obj in sequence


# NB: |add is provided by Django
@register.filter
def sub(x, y):
    """Subtraction operator."""
    return x - y


@register.filter
def mult(x, y):
    """Multiplication operator."""
    return x * y


@register.filter
def idiv(integer1, integer2):
    """Integer division operator."""
    return integer1 // integer2


# TODO ?
# @register.filter
# def div(x, y):
#     return x / y


@register.filter
def mod(integer1, integer2):
    """Modular operator."""
    return integer1 % integer2


@register.filter(name='range')
def range_filter(integer, start=0):
    """Create a range iterator.
    @param integer: number of element in the range.
    @param start: first value of the range.
    """
    return range(start, start + integer)


@register.filter
def has_attr(o, attr_name):
    return hasattr(o, attr_name)


# NB: seems not used any more...
@register.filter
def is_iterable(iterable):
    return hasattr(iterable, '__iter__')


@register.filter
def is_plural(x):
    """Is a number considered a plural in the current language."""
    return plural(x)


@register.filter(name='format')
def format_string(value, format_str):
    """Build a string from a format-string with one '%s' element.

    Example:
        <span>{{ nick_name|format:'Hello %s' }}</span>
    """
    return format_str % value


# TODO: other flavours -> brace_positional, classical_named...
@register.simple_tag
def format_string_brace_named(format_str, **kwargs):
    """Build a string from a format-string using braced+named arguments.

    Example:
        <h2>{% format_string_brace_named _('Hello {nick_name}') nick_name='Joe' %}</h2>
    """
    return format_str.format(**kwargs)


# NB: seems not used any more...
@register.filter
def to_timestamp(date):
    return str(int(date.timestamp()))


@register.filter
def uca_sort(iterable):
    """Get a sorted list of strings, using a correct order for unicode characters."""
    strs = [str(e) for e in iterable]
    strs.sort(key=collator.sort_key)

    return strs


@register.filter
def verbose_models(models):
    return [m._meta.verbose_name for m in models]


@register.filter
# def allowed_str(entity, user):
def allowed_str(instance, user):
    # return entity.allowed_str(user)
    return instance.allowed_str(user) if hasattr(instance, 'allowed_str') else instance


@register.filter
def format_amount(amount, currency_or_id=None):
    return currency(amount, currency_or_id)


@register.filter('is_ajax')
def request_is_ajax(request):
    return is_ajax(request)


@register.filter
def optionize_model_iterable(iterable, type='tuple'):
    """Build a choices-friendly generator from an iterable of instances."""
    if type == 'dict':
        return ({'value': model.id, 'label': str(model)} for model in iterable)
    else:
        return ((model.id, str(model)) for model in iterable)


@register.filter
def jsonify(value):
    return json_encode(value)


@register.filter
def filter_empty(iterable):
    """Build a list from an iterable object but without the empty elements.
    Empty means here "evaluated as False", like '', [], (), None...
    """
    return [x for x in iterable if x]


_css_escapes = {
    ord('>'): r'\003E ',
    ord('<'): r'\003C ',
    ord('&'): r'\0026 ',
    ord('"'): r'\0022 ',
    ord("'"): r'\0027 ',
}


@register.filter('escapecss')
def escape_css(value):
    """Escape a value used in a CSS "content" property."""
    return mark_safe(str(value).translate(_css_escapes).strip())


@register.simple_tag
def listify(*args):
    """Build a list from several arguments.
    It can be useful to build a parameter for another tag.
    """
    return [*args]


@register.simple_tag
def jsondata(value, **kwargs):
    """ Encode and render json data in a <script> tag with attributes.

    {% jsondata data arg1=foo.bar arg2='baz' %}
    """
    if value is None:
        return ''

    if kwargs.pop("type", None) is not None:
        logger.warning('jsondata tag do not accept custom "type" attribute')

    content = jsonify(value) if not isinstance(value, str) else value
    attrs = ''.join(f' {k}="{escape(v)}"' for k, v in kwargs.items())

    return mark_safe(
        f'<script type="application/json"{attrs}><!-- {escapejson(content)} --></script>'
    )


@register.simple_tag
def get_efilter_conditions(efilter, user):
    return [*efilter.get_verbose_conditions(user)]


# TODO: deprecate ? (not used)
@register.simple_tag
def get_entity_summary(entity, user):
    return entity.get_entity_summary(user)


@register.simple_tag(takes_context=True)
def get_entity_html_attrs(context, entity):
    return format_html_join(' ', '{}="{}"', entity.get_html_attrs(context).items())


# TODO: move to <creme.creme_core.utils> ?
# See grouper implementation: https://docs.python.org/3/library/itertools.html#itertools-recipes
@register.filter
def grouper(value, n):
    """Group elements of an iterable.
    @param value: iterable object.
    @param n: size of the groups.
    """
    args = [iter(value)] * n
    return zip_longest(fillvalue=None, *args)


# TODO: is 'callback_url' still useful with the JS feature "comeback"?
@register.simple_tag
def inner_edition_uri(instance, cells, callback_url=None):
    # TODO: pass the registry in context? accept it as argument?
    uri = bulk_update_registry.inner_uri(
        instance=instance,
        cells=[cells] if isinstance(cells, EntityCell) else cells,
    )

    # if callback_url:
    if callback_url and uri:
        uri += f'&callback_url={callback_url}'

    return uri


@register.filter
def url(url_name, arg=None):
    return reverse(url_name, args=None if arg is None else (arg,))


@register.simple_tag
def url_join(*args, **params):
    """ Add some GET parameters to a URL.
    It's work even if the URL has already some GET parameters.

    {% url_join my_url arg1=foo.bar arg2='baz' as my_uri %}
    """
    if not args:
        return ''

    # NB: we take the base URL with *args in order to allow all values for GET keys.
    if len(args) > 1:
        raise TemplateSyntaxError(
            '"url_join" takes one & only one positional argument (the base URL)'
        )

    base = args[0]

    if not base:
        return ''
    # TODO: base = str(base) ?

    if not params:
        uri = base
    elif urlsplit(base).query:  # There are already some GET params
        uri = base + '&' + urlencode(params, doseq=True)
    else:
        uri = base + '?' + urlencode(params, doseq=True)

    return mark_safe(uri)


# TAG : "templatize"------------------------------------------------------------
_templatize_re = compile_re(r'(.*?) as (\w+)')


@register.tag(name='templatize')
def do_templatize(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError as e:
        raise TemplateSyntaxError(
            f'"{token.contents.split()[0]}" tag requires arguments'
        ) from e

    match = _templatize_re.search(arg)
    if not match:
        raise TemplateSyntaxError(
            f'"{tag_name}" tag has invalid arguments: <{arg}>'
        )

    template_string, var_name = match.groups()

    first_char = template_string[0]
    if not (first_char == template_string[-1] and first_char in {'"', "'"}):
        raise TemplateSyntaxError(
            f'''"{tag_name}" tag's argument should be in quotes.'''
        )

    return TemplatizeNode(template_string[1:-1], var_name)


class TemplatizeNode(TemplateNode):
    def __init__(self, template_string, var_name):
        self.inner_template = Template(template_string)
        self.var_name = var_name

    def __repr__(self):
        return '<Templatize node>'

    def render(self, context):
        context[self.var_name] = self.inner_template.render(context)
        return ''


# TAG : "print_field"-----------------------------------------------------------

# TODO: need a templatetag to build a ViewTag?
# TODO: pass the registry in the context? pass the user as argument?
@register.simple_tag(takes_context=True)
def print_field(context, *, object, field, tag=ViewTag.HTML_DETAIL):
    return field_printers_registry.get_field_value(
        instance=object,
        field_name=field,
        user=context['user'],
        tag=tag,
    )


# TAG : "has_perm_to" [DEPRECATED]----------------------------------------------

_haspermto_re = compile_re(r'(\w+) (.*?) as (\w+)')


def _can_create(model_or_ct, user):
    ct = (
        model_or_ct
        if isinstance(model_or_ct, ContentType) else
        ContentType.objects.get_for_model(model_or_ct)
    )
    return user.has_perm(f'{ct.app_label}.add_{ct.model}')


def _can_export(model_or_ct, user):
    ct = (
        model_or_ct
        if isinstance(model_or_ct, ContentType) else
        ContentType.objects.get_for_model(model_or_ct)
    )
    return user.has_perm(f'{ct.app_label}.export_{ct.model}')


_PERMS_FUNCS = {
    'create': _can_create,
    'export': _can_export,
    'view':   lambda entity, user: user.has_perm_to_view(entity),
    'change': lambda entity, user: user.has_perm_to_change(entity),
    'delete': lambda entity, user: user.has_perm_to_delete(entity),
    'link':   lambda entity_or_model, user: user.has_perm_to_link(entity_or_model),
    'unlink': lambda entity, user: user.has_perm_to_unlink(entity),
    'access': lambda app_name, user: user.has_perm_to_access(app_name),
    'admin':  lambda app_name, user: user.has_perm_to_admin(app_name),
}


@register.tag(name='has_perm_to')
def do_has_perm_to(parser, token):
    """{% has_perm_to TYPE OBJECT as VAR %}
    Example: {% has_perm_to change action.creme_entity as has_perm %}

    TYPE: must be in ('create', 'view', 'change', 'delete', 'link', 'unlink',
          'export', 'access', 'admin')
    OBJECT: * TYPE in ('view','change', 'delete', 'unlink') => must be a CremeEntity instance.
            * TYPE='link' => can be a CremeEntity instance or a class inheriting CremeEntity.
            * TYPE in ('create', 'export') => can be a CremeEntity instance,
              a class inheriting CremeEntity or a ContentType instance.
            * TYPE in ('access', 'admin') => an app name, like "creme_core".
    """
    warnings.warn(
        'The template-tag {% has_perm_to %} is deprecated; '
        'use the template-filters of the library "creme_perms" instead.',
        DeprecationWarning,
    )

    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError as e:
        raise TemplateSyntaxError(
            f'"{token.contents.split()[0]}" tag requires arguments'
        ) from e

    match = _haspermto_re.search(arg)
    if not match:
        raise TemplateSyntaxError(
            f'"{tag_name}" tag had invalid arguments: <{arg}>'
        )

    perm_type, entity_path, var_name = match.groups()

    perm_func = _PERMS_FUNCS.get(perm_type)
    if not perm_func:
        raise TemplateSyntaxError(
            f'"{tag_name}" invalid permission tag: "{perm_type}"'
        )

    entity_var = TemplateLiteral(parser.compile_filter(entity_path), entity_path)

    return HasPermToNode(perm_func, entity_var, var_name)


class HasPermToNode(TemplateNode):
    def __init__(self, perm_func, entity_var, var_name):
        self.perm_func = perm_func
        self.entity_var = entity_var
        self.var_name = var_name

    def __repr__(self):
        return '<HasPermTo node>'

    def render(self, context):
        var = self.entity_var.eval(context)  # Can raise template.VariableDoesNotExist...
        user = context['user']
        context[self.var_name] = self.perm_func(var, user)

        return ''

# TAG : "has_perm_to [end]------------------------------------------------------


@register.tag(name='include_creme_media')
def do_include_creme_media(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError as e:
        raise TemplateSyntaxError(
            f'{token.contents.split()[0]!r} tag requires arguments'
        ) from e

    return MediaNode(TemplateLiteral(parser.compile_filter(arg), arg))


class MediaNode(TemplateNode):
    def __init__(self, bundle_var):
        self.bundle_var = bundle_var

    def render(self, context):
        bundle = self.bundle_var.eval(context)

        return _render_include_media(context['THEME_NAME'] + bundle, variation={})


@register.simple_tag(name='scm_info')
def get_scm_info():
    from ..utils import version

    scm = settings.SCM

    if scm == 'git':
        return version.get_git_info

    if scm == 'hg':
        return version.get_hg_info

    return None


@register.tag(name='blockjsondata')
def do_jsondata(parser, token):
    """ Encode json of the block and render it in a <script> tag with attributes.

    {% blockjsondata arg1=foo.bar arg2='baz' %}
        {{data}}
    {% endblockjsondata %}
    """
    nodelist = parser.parse(('endblockjsondata',))
    parser.delete_first_token()
    kwargs = token_kwargs(token.split_contents()[1:], parser)
    return JsonScriptNode(nodelist, kwargs)


class JsonScriptNode(TemplateNode):
    def __init__(self, nodelist, kwargs):
        self.nodelist = nodelist
        self.kwargs = kwargs

    def render(self, context):
        output = self.nodelist.render(context)
        kwargs = self.kwargs

        if kwargs.pop("type", None) is not None:
            logger.warning('jsondatablock tag do not accept custom "type" attribute')

        attrs = ''.join(
            f' {k}="{escape(force_str(v.resolve(context)))}"'
            for k, v in kwargs.items()
        )

        return mark_safe(
            f'<script type="application/json"{attrs}><!-- {escapejson(output)} --></script>'
        )
