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
from base64 import b64encode
from io import BytesIO
from os.path import splitext

from django.conf import settings
from django.template import Library
from django.template import Node as TemplateNode
from django.template import TemplateSyntaxError
from django.utils.html import escape, format_html
from django.utils.html import urlize as django_urlize
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from PIL.Image import open as open_img

from ..gui.icons import (
    BaseIcon,
    get_icon_by_name,
    get_icon_size_px,
    icon_registry,
)
from ..utils.media import get_current_theme_from_context
from . import KWARG_RE

register = Library()
logger = logging.getLogger(__name__)


# WIDGET ICON ------------------------------------------------------------------

class IconNode(TemplateNode):
    def __init__(self, size_var=None, label_var=None, class_var=None, asvar_name=None):
        self.size_var = size_var
        self.label_var = label_var
        self.class_var = class_var
        self.asvar_name = asvar_name

    def _build_icon(self, context, theme, size_px, label, css_class):
        raise NotImplementedError

    def render(self, context):
        theme = get_current_theme_from_context(context)

        def resolve(var, default):
            return var.resolve(context) if var is not None else default

        icon = self._build_icon(
            context,
            theme=theme,
            size_px=get_icon_size_px(theme, resolve(self.size_var, 'medium')),
            label=resolve(self.label_var, ''),
            css_class=resolve(self.class_var, ''),
        )

        if self.asvar_name:
            context[self.asvar_name] = icon
            return ''
        else:
            return icon.render()


class NamedIconNode(IconNode):
    def __init__(self, name_var, **kwargs):
        super().__init__(**kwargs)
        self.name_var = name_var

    def _build_icon(self, context, theme, size_px, label, css_class):
        return get_icon_by_name(self.name_var.resolve(context), theme, size_px, label, css_class)


class ContentTypeIconNode(IconNode):
    def __init__(self, ctype_var, **kwargs):
        super().__init__(**kwargs)
        self.ctype_var = ctype_var

    def _build_icon(self, context, theme, size_px, label, css_class):
        model = self.ctype_var.resolve(context).model_class()

        # TODO: how to pass the registry in the context ? (context_processor?)
        icon = icon_registry.get_4_model(model=model, theme=theme, size_px=size_px)
        icon.css_class = css_class

        if label:
            icon.label = label

        return icon


class InstanceIconNode(IconNode):
    def __init__(self, instance_var, **kwargs):
        super().__init__(**kwargs)
        self.instance_var = instance_var

    def _build_icon(self, context, theme, size_px, label, css_class):
        instance = self.instance_var.resolve(context)

        # TODO: see ContentTypeIconNode._build_icon
        icon = icon_registry.get_4_instance(instance=instance, theme=theme, size_px=size_px)
        icon.css_class = css_class

        if label:
            icon.label = label

        return icon


class DataIconNode(IconNode):
    def __init__(self, data_var, **kwargs):
        super().__init__(**kwargs)
        self.data_var = data_var

    def _build_icon(self, context, theme, size_px, label, css_class):
        path = self.data_var.resolve(context)

        # TODO: extract this class?
        class InlinedIcon(BaseIcon):
            # TODO: accept bytes? PIl.Image?
            def __init__(this, path: str, *args, **kwargs):
                super().__init__(*args, **kwargs)
                this.path = path

            def render(this, css_class=''):
                final_css_class = this.css_class + css_class

                with open(this.path, 'rb') as img:
                    _base_path, extension = splitext(path)
                    file_data = img.read()

                    # TODO: store width & height?
                    with open_img(BytesIO(file_data)) as img:
                        width, height = img.size

                    img_data = b64encode(file_data).decode()

                if width > height:
                    size_attr = 'width'
                    # NB: we pad in order to center vertically the image
                    # tips: "this.size * height / width" gives the scaled height
                    padding = (this.size - int(round(this.size * height / width))) // 2
                    style = f'padding-top: {padding}px;' if padding else ''
                else:
                    size_attr = 'height'
                    style = ''

                return format_html(
                    '<img src="{url}" {attrs}title="{label}" alt="{label}" '
                    '{size_attr}="{size}px" style="{style}"/>',
                    size_attr=size_attr,
                    size=this.size,
                    label=this.label,
                    attrs=format_html('class="{}" ', final_css_class) if final_css_class else '',
                    url=f'data:image/{extension[1:]};base64, {img_data}',
                    style=style,
                )

        return InlinedIcon(path, size=size_px, label=label)


__ICON_ARGS_MAP: dict[str, str] = {
    'size':  'size_var',
    'label': 'label_var',
    'class': 'class_var',
}
_WIDGET_ICON_NODES: dict[str, tuple[str, type[IconNode]]] = {
    'name':     ('name_var',     NamedIconNode),
    'ctype':    ('ctype_var',    ContentTypeIconNode),
    'instance': ('instance_var', InstanceIconNode),
    'data':     ('data_var',     DataIconNode),
}


@register.tag(name='widget_icon')
def do_icon(parser, token):
    """ Get an Icon (i.e. <img>).

    A. The icon can be rendered immediately:
            {% widget_icon name='add' %}

       or be assigned to a context variable:
           {% widget_icon name='add' as add_icon %}
           {# the icon can then be rendered like this ... #}
           {{add_icon.render}}
           {# ... or like this with an additional CSS class #}
           {% widget_render_icon add_icon class='my-icon-class' %}

    B. The first argument can have 3 types:
       name='foobar' => An icon with 'foobar' as base name is searched in the
           images/ directory of the current theme.
       ctype=content_type_instance  => The icon associated to this ContentType
           is used (see icon_registry.register()).
       instance=my_instance => The icon associated to this instance is used
           (see icon_registry.register_4_instance()).
       data='path_to_an_image_file' => The image is inlined in the "src"
           attribute (the theme is only used to compute the "width" attribute).

    C. The other arguments are:
       - size: a String in big/medium/small/brick-header/global-button/...
         (creme.creme_core.gui.icons._ICON_SIZES_MAP)
       - label
       - class: the CSS classes in the <img> node.
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError(
            f'"{bits[0]}" takes at least one argument (name/ctype/instance=...)'
        )

    match = KWARG_RE.match(bits[1])
    if not match:
        raise TemplateSyntaxError('Malformed 1rst argument to "widget_icon" tag.')

    # First argument
    fa_name, fa_value = match.groups()
    try:
        arg_name, icon_node_cls = _WIDGET_ICON_NODES[fa_name]
    except KeyError as e:
        raise TemplateSyntaxError(
            f'Invalid 1rst argument to "widget_icon" tag ; '
            f'it must be in {_WIDGET_ICON_NODES.keys()}'
        ) from e

    kwargs = {arg_name: parser.compile_filter(fa_value)}

    bits = bits[2:]
    if len(bits) >= 2 and bits[-2] == 'as':
        kwargs['asvar_name'] = bits[-1]
        bits = bits[:-2]

    for bit in bits:
        match = KWARG_RE.match(bit)
        if not match:
            raise TemplateSyntaxError(f'Malformed arguments to "widget_icon" tag: {bit}')

        name, value = match.groups()

        arg_name = __ICON_ARGS_MAP.get(name)
        if arg_name is None:
            raise TemplateSyntaxError(f'Invalid argument name to "widget_icon" tag: {name}')

        kwargs[arg_name] = parser.compile_filter(value)

    return icon_node_cls(**kwargs)


@register.tag(name='widget_render_icon')
def do_render_icon(parser, token):
    """Render an Icon with additional CSS classes.

    E.g.
      {% widget_icon name='add' class='A' as my_icon %}
      {% widget_render_icon my_icon class='B' %} {# Outputs <img class="A B" ...> #}
    """
    bits = token.split_contents()

    if len(bits) != 3:
        raise TemplateSyntaxError(f'"{bits[0]}" takes 2 arguments (icon & class)')

    def compile_arg(token, prefix):
        if token.startswith(prefix):
            token = token.removeprefix(prefix)

        return parser.compile_filter(token)

    return IconRendererNode(
        icon_var=compile_arg(bits[1], 'icon='),
        class_var=compile_arg(bits[2], 'class='),
    )


class IconRendererNode(TemplateNode):
    def __init__(self, icon_var, class_var):
        self.icon_var = icon_var
        self.class_var = class_var

    def render(self, context):
        return self.icon_var.resolve(context).render(css_class=self.class_var.resolve(context))


# WIDGET ICON [END] ------------------------------------------------------------

# TODO: "target" argument?
@register.simple_tag
def widget_hyperlink(instance, label=None, disabled: bool | str = False):
    """ Prints a <a> tag referencing the page of a model instance.
    @param instance: Instance of DjangoModel which has a method 'get_absolute_url()'
           BEWARE: it must not be a CremeEntity instance, or an auxiliary instance,
           because the permissions are not checked.
    @param label: String used as label of the link; by default the label used is
           'instance.__str__()'.
    @param disabled: Indicates if the link should be a simple label.
           - False (default value) or empty string => the link is enabled.
           - True => simple label.
           - Not empty string => a simple label with the string used as tooltip
             to indicate the reason of the disabling.

    E.g.
       {% widget_hyperlink my_instance %}
       {% widget_hyperlink my_instance 'My favorite instance' %}
       {% widget_hyperlink my_instance disabled='You must be a superuser' %}
    """
    txt = label or str(instance)

    if disabled:
        return format_html(
            '<span class="disabled-link">{label}</span>',
            label=txt,
        ) if isinstance(disabled, bool) else format_html(
            '<span class="disabled-link" title="{title}">{label}</span>',
            label=txt, title=disabled,
        )

    try:
        return format_html(
            '<a href="{url}">{label}</a>',
            url=instance.get_absolute_url(),
            label=txt,
        )
    except AttributeError:
        logger.warning(
            'Tag {%% widget_hyperlink %%} use with an instance with no absolute url: %s',
            instance,
        )

        # NB: we do not use label; the template-tag just prints a string in this case.
        return escape(instance)


@register.simple_tag
def widget_ctype_hyperlink(ctype, user):
    """ Prints a <a> tag referencing the page of a model instance.
    @param instance: Instance of DjangoModel which has a method 'get_absolute_url()'
           BEWARE: it must not be a CremeEntity instance, or an auxiliary instance,
           because the permissions are not checked.
    @param label: String used as label of the link; by default the label used is
           'instance.__str__()'.

    E.g.
       {% widget_hyperlink my_instance %}
       {% widget_hyperlink my_instance 'My favorite instance' %}
    """
    model = ctype.model_class()
    verbose_name = model._meta.verbose_name_plural
    get_url = getattr(model, 'get_lv_absolute_url', None)

    if not get_url or not user.has_perm_to_access(model._meta.app_label):
        return str(verbose_name)

    return format_html(
        '<a href="{url}">{name}</a>', url=get_url(), name=verbose_name,
    )


@register.simple_tag
def widget_entity_hyperlink(entity, user, ignore_deleted=False, label=None,
                            target: str = '_self',  # TODO: Literal? Enum?
                            relative: bool = True,
                            ):
    """Prints a <a> tag referencing the detail-view of an entity instance.
    @param entity: Instance of a model inheriting CremeEntity which has
           overridden the method 'get_absolute_url()'.
    @param user: 'django.contrib.auth.get_user_model()' instance corresponding
           to the logged user (in order to use credentials correctly).
    @param ignore_deleted: Boolean indicating if entities marked as deleted should
           be display like other ones. Default value is 'False'.
    @param label: String used as label of the link; by default the label used is
           'entity.__str__()'.
    @param target: Used to build the HTML attribute <target="...">.
           So the value should be in: "_self", "_blank", "_parent", "_top".
    @param relative: is the URL relative? If False, 'settings.SITE_DOMAIN' is
           used to build an absolute URL.

    E.g.
      {% widget_entity_hyperlink my_entity user %}
      {% widget_entity_hyperlink my_entity user ignore_deleted=True %}
      {% widget_entity_hyperlink my_entity user label='An interesting entity' %}
      {% widget_entity_hyperlink my_entity user target='_blank' %}
    """
    entity = entity.get_real_entity()

    if user.has_perm_to_view(entity):
        url = entity.get_absolute_url()

        return format_html(
            '<a href="{url}" target="{target}"{deleted}>{label}</a>',
            url=url if relative else settings.SITE_DOMAIN + url,
            target=target,
            deleted=(
                mark_safe(' class="is_deleted"')
                if entity.is_deleted and not ignore_deleted else
                ''
            ),
            label=label or entity,
        )

    return settings.HIDDEN_VALUE


@register.inclusion_tag('creme_core/templatetags/widgets/enumerator.html')
def widget_enumerator(items, threshold=3, empty='', summary=None):
    """Enumerate a list of items in a compact manner.
    If the number of items exceed a given threshold, another way to display the
    items is used (currently an inner popup).
    @param items: Sequence of objects.
    @param threshold: Integer >= 2.
    @param empty: Message (string) used when <items> is empty.
    @param summary: Format string used when there are too many items.
           It used the brace format with "count" name (i.e. '{count} foobars').
           If not given default one is provided.
    """
    return {
        'items': items,
        'threshold': threshold,
        'empty_label': empty,
        'summary': summary,
    }


@register.inclusion_tag('creme_core/templatetags/widgets/help-sign.html')
def widget_help_sign(message, icon='info'):
    return {'message': message, 'icon': icon}


@register.tag(name='widget_join')
def do_join(parser, token):
    """ Joins the items of an enumeration (i.e. for loop) in a pretty way.
    Must be used inside a for loop.

    Example:
    {% for item in items %}
        {% widget_join %}<strong>{{item}}</strong>{% end_widget_join %}
        {% empty %}No item
    {% endfor %}
    """
    tokens = token.contents.split(None, 2)

    if len(tokens) > 1:
        # We are sure there are at least one token (the tag itself).
        raise TemplateSyntaxError(f'"{tokens[0]}" tag takes no argument')

    nodelist = parser.parse(('end_widget_join',))
    parser.delete_first_token()

    return JoinNode(nodelist)


def enum_comma_and(item, counter, is_first, is_last):
    if is_first:
        return item

    if is_last:
        return '&emsp14;{}&emsp14;{}'.format(_('and'), item)

    return f',&emsp14;{item}'


class JoinNode(TemplateNode):
    behaviours = {
        '':   enum_comma_and,  # Default
        'en': enum_comma_and,
        'fr': enum_comma_and,
    }

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        try:
            forloop = context['forloop']
        except KeyError as e:
            raise ValueError(
                'The tag {% widget_join %} must be used inside a {% for %} loop.'
            ) from e

        try:
            behaviour = self.behaviours[context['LANGUAGE_CODE']]
        except KeyError:
            behaviour = self.behaviours['']

        return behaviour(
            self.nodelist.render(context), counter=forloop['counter0'],
            is_first=forloop['first'], is_last=forloop['last'],
        )


@register.filter
def widget_urlize(value, trim_url_limit=None, nofollow=False, autoescape=True):
    if settings.URLIZE_TARGET_BLANK:
        url_ized = django_urlize(
            value, trim_url_limit=trim_url_limit, nofollow=False, autoescape=autoescape,
        ).replace('<a', '<a target="_blank" rel="noopener noreferrer"')
    else:
        url_ized = django_urlize(
            value, trim_url_limit=trim_url_limit, nofollow=nofollow, autoescape=autoescape,
        )

    return mark_safe(url_ized) if autoescape else url_ized
