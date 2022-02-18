# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

from django.template import Library, TemplateSyntaxError
from django.template.base import TextNode
from django.utils.safestring import SafeData, mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ..core import sorter
from ..core.entity_cell import EntityCellRegularField
# NB: do not import registries directly to facilitate unit tests
from ..gui import bricks, bulk_update
from ..gui.bricks import Brick, BricksManager
from ..gui.pager import PagerContext
from ..utils.media import get_current_theme_from_context
from ..utils.translation import plural as is_plural
from ..views.entity import _bulk_has_perm
from .creme_widgets import get_icon_by_name, get_icon_size_px

register = Library()
logger = logging.getLogger(__name__)


# TODO: 'selection_title' really need to be hard coded ? kwargs + html attr instead ?
#       (generate an 'indicator' as loading => merge this concepts ??)
@register.inclusion_tag('creme_core/templatetags/bricks/title.html', takes_context=True)
def brick_header_title(context, title,
                       plural=None, empty=None, icon='info',
                       count=None, selection_title=None, selection_plural=None,
                       ):
    """Display the title of a brick.
    Should be used in the template block 'brick_header_title'.

    @param context: Template context.
    @param title: Title of the brick. If you want to display a number of items
           (eg: number of lines in this brick) & so pluralize the title, use a
           format variable '{count}' and the parameter 'plural'.
    @param plural: Title to use with a plural number of items. If you set it,
           it must use format variable '{count}' & the parameter 'title' too.
    @param empty: Title to use it there no items in the bricks.
    @param icon: The string identifying an Icon (eg: 'add'), or an Icon instance
           (see the templatetag {% widget_icon  %} of the lib creme_widget.
           Default is 'info' icon.
    @param count: Number of items in the bricks. If you don't set it, & the
           brick is paginated, the paginator's count is used.
    @param selection_title: Additional text displayed in title of bricks which
           allows to select items. The related brick must have the class
           'brick-selectable' & a column with class 'data-selectable-selector-column'.
           Must use a format variable '%s'.
           If set, the parameter 'selection_plural' must be set too.
    @param selection_plural: See 'selection_title'.

    Example 1 - basic text with info icon:
        {% extends 'creme_core/bricks/base/base.html' %}
        {% load i18n creme_bricks %}

        {% block brick_header_title %}
            {% brick_header_title title=_('Customers and providers') %}
        {% endblock %}

        ...

    Example 2 - paginated & named icon:
        {% extends 'creme_core/bricks/base/paginated-table.html' %}
        {% load i18n creme_bricks %}

        {% block brick_header_title %}
            {% brick_header_title
               title=_('{count} Customers') plural=_('{count} Customers')
               empty=_('Customers') icon='phone' %}
        {% endblock %}

        ...

    Example 3 - instanced icon (notice the size):
        {% extends 'creme_core/bricks/base/list.html' %}
        {% load i18n creme_bricks creme_widgets %}

        {% block brick_header_title %}
            {% widget_icon ctype=my_ct size='brick-header' as my_icon %}
            {% brick_header_title title=my_title icon=my_icon %}
        {% endblock %}

        ...
    """
    if count is None:
        count = context.get('page').paginator.count if 'page' in context else 0

    if count == 0:
        title_fmt = empty or title
    elif is_plural(count):
        title_fmt = plural or title
    else:
        title_fmt = title

    rendered_title = title_fmt.format(count=count)
    if isinstance(title_fmt, SafeData):
        rendered_title = mark_safe(rendered_title)

    if isinstance(icon, str):
        # TODO: cache ?
        theme = get_current_theme_from_context(context)
        icon = get_icon_by_name(
            icon, theme,
            size_px=get_icon_size_px(theme, size='brick-header'),
            label=_('Information') if icon == 'info' else rendered_title,
        )

    return {
        'title': rendered_title,
        'icon': icon,
        'selection_title': selection_title,
        'selection_plural': selection_plural,
    }


DEFAULT_ACTION_LABELS = {
    'edit':   gettext_lazy('Edit'),
    'delete': gettext_lazy('Delete'),
}

_DISPLAY_VALUES = frozenset(('text', 'icon', 'both'))


@register.inclusion_tag('creme_core/templatetags/bricks/action.html', takes_context=True)
def brick_action(context, id, url='',
                 label=None, icon=None, icon_size='brick-action', display='icon',
                 enabled=True,
                 confirm=None, loading=None, help_text=None,
                 **kwargs):
    """Create a Creme-action (ie: link/button related to JavaScript code) made
    for use in a brick.
    (see  creme/creme_core/static/creme_core/js/bricks.js).

    This kind of action will reload the brick (& its dependencies) when it's needed.
    There are more specialised templatetags (wrappers) for specific
    context (brick header, table-brick):
      {% brick_header_action .. %}, {% brick_table_action ... %}...

    @param context: Template context.
    @param id: ID of the action. An ID 'foo-bar' will correspond to the method
           '_action_foo_bar' of the brick.
           Description of the actions defined by the core (some apps define their
           own actions, bind to their own bricks):
            - add: displays an inner-popup designed to contains a form.
              Only need the parameter 'url' to be filled.
            - edit: idem.
            - link: idem.
            - add-relationships: displays a list-view in an inner-popup, &
              creates Relations with selected entities.
              The 'url' parameter is ignored, but the following data must be provided:
                    __subject_id: ID of the <subject> entity.
                    __rtype_id: ID of the used RelationType.
                    __ctype_id: ID of the ContentType of the <object> entities
                    (which are selected by the user).
                This data is optional:
                     __multiple: True means 'multi-selection'.
                TODO: automatically use icon='link'.
            - delete: sends a POST request data to the given 'url', using action's
              data (see kwargs) as POST data.
              The user has to confirm (a default confirmation message is provided
              if it's not set).
            - update: sends a POST request data to the given 'url', using
              action's data (see kwargs) as POST data.
            - update-redirect: idem as 'update', but the page is redirected with
              the URL sent by the server in its response.
            - view: displays an inner-popup designed to contains an HTML fragment.
              You have to fill the parameter 'url'.
              The extra data '__title' is optional (title of the inner-popup).
            - redirect: redirect the page to the given 'url'.
            - refresh: reload the brick & its dependencies (internal use)
    @param url: URL (string) used by the action (creation, edition etc...).
           Most of the actions need the URL to be given (see 'id' documentation).
    @param label: String. Default labels are available for some action IDs
           (see DEFAULT_ACTION_LABELS), if not, the placeholder 'Information' will be used.
    @param icon: The string identifying an Icon (eg: 'add'), or an Icon instance
           (see the templatetag {% widget_icon  %} of the lib creme_widget).
           Default is None ; but when an icon is need (parameter 'display' is
           'icon or 'both') but no 'icon' is given, the parameter 'type' & 'id'
           are used as icon name (so actions like 'add' use a default icon).
    @param icon_size: Size-tag (see creme/creme_core/gui/icons.py -> _ICON_SIZES_MAP).
           Only useful if you pass a string as 'icon' parameter.
           Default is 'brick-action'.
           Notice that wrappers (brick_header_action, brick_table_action etc...)
           will pass a correct size for them.
    @param display: String in {'text', 'icon', 'both'} ('both' means 'text' AND 'icon'}.
           Default is 'icon' (but wrappers can override this default value).
    @param enabled: Boolean indicating if the action must be active
           (generally used for with credentials check).
           Default is True.
    @param confirm: Confirmation message. A not empty message means that a
           confirmation popup is displayed with this message.
           Default is None.
    @param loading: Loading message.
    @param help_text: String. Same as label if not defined.
    @param kwargs:
           These keys have a precise meaning:
                - 'type': String used to generate the CSS class "action-type-{{action_type}}" ;
                          classical provided types are the actions IDs (add, edit...)
                - 'class': Extra CSS class.
           Remaining keys must start with '__' ; they are serialised to JSON &
           can be used by the code of the action.
    """
    assert display in _DISPLAY_VALUES

    action_type = kwargs.pop('type', id)
    css_class   = kwargs.pop('class', '')
    properties = []
    action_options = {}

    if icon is None and display != 'text':
        icon = action_type

    if label is None:
        label = DEFAULT_ACTION_LABELS.get(action_type, None) or _('Information')

    if not help_text:
        help_text = label

    if isinstance(icon, str):
        theme = get_current_theme_from_context(context)
        icon = get_icon_by_name(
            icon, theme,
            size_px=get_icon_size_px(theme, icon_size), label=help_text,
        )

    def _clean_extra_data(data, prefix='__'):
        prefix_length = len(prefix)
        extra_data = {}

        for key, value in data.items():
            if not key.startswith(prefix):
                raise TemplateSyntaxError(
                    f'The key "{key}" does not starts with {prefix}'
                )

            extra_data[key[prefix_length:]] = value

        return extra_data

    if not enabled:
        properties.append('is-disabled')

    if loading:
        properties.append('is-async-action')

        if isinstance(loading, str):
            action_options['loading'] = loading

    if confirm:
        action_options['confirm'] = confirm

    action_extra_data = _clean_extra_data(kwargs)
    data = {
        'url':      url,
        'disabled': not enabled,

        'label':     label,
        'help_text': help_text,
        'icon':      icon,
        'display':   display,

        'action_id':   id,
        'action_type': action_type,

        'properties': ' '.join(properties),
        'class':      css_class,
        'loading':    bool(loading),

        'data': None,
    }

    if action_options or action_extra_data:
        data['data'] = {
            'options': action_options,
            'data': action_extra_data,
        }

    return data


@register.inclusion_tag(
    'creme_core/templatetags/bricks/header-action.html',
    takes_context=True
)
def brick_header_action(context, display='both', **kwargs):
    """Action (see brick_brick_action()) for brick's header.

    Example:
        {% extends 'creme_core/bricks/base/base.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_header_actions %}
            {% brick_header_action id='add' url=creation_url
               label=_('Add a stuff') enabled=can_create_stuff %}
        {% endblock %}

        ...
    """
    return brick_action(context, display=display, **kwargs)


@register.inclusion_tag(
    'creme_core/templatetags/bricks/card-button.html',
    takes_context=True,
)
def brick_card_button(context, action, url, label,
                      icon=None, enabled=True, confirm=None,
                      **kwargs):
    """Action (see brick_brick_action()) for "card" (hat) bricks.

    Notice that the size of instanced Icons should be "brick-hat-card-button".
    """
    return brick_action(
        context,
        id=action, url=url,
        label=label, icon=icon, icon_size='brick-hat-card-button',
        enabled=enabled, confirm=confirm,
        **kwargs
    )


@register.inclusion_tag(
    'creme_core/templatetags/bricks/bar-button.html',
    takes_context=True,
)
def brick_bar_button(context, action, url, label, icon,
                     enabled=True, confirm=None,
                     **kwargs):
    """Action (see brick_brick_action()) for "bar" (hat) bricks.

    Notice that the size of instanced Icons should be "brick-hat-bar-button".
    """
    return brick_action(
        context,
        id=action, url=url,
        label=label, icon=icon, icon_size='brick-hat-bar-button',
        enabled=enabled, confirm=confirm,
        **kwargs
    )


@register.inclusion_tag(
    'creme_core/templatetags/bricks/menu-action.html',
    takes_context=True,
)
def brick_menu_action(context, id, **kwargs):
    """Action (see brick_brick_action()) for the (hidden menu) of a brick.

    Example:
        {% extends 'creme_core/bricks/base/base.html' %}
        {% load i18n creme_core_tags creme_bricks %}

        ...

        {% block brick_menu_actions %}
            {{block.super}}

            <hr/>
            {% brick_menu_action id='edit' url=config_url icon='config'
               label=_('Configure the block') enabled=config_perm %}
        {% endblock %}

        ...
    """
    return brick_action(context, id=id, icon_size='brick-menu-action', **kwargs)


def _brick_menu_state_action(
        context, action_id, current_state, in_label, out_label, icon='view_less',
        **kwargs):
    return brick_action(
        context, id=action_id,
        icon=icon,
        label=in_label if current_state else out_label,
        __inlabel=in_label,
        __outlabel=out_label,
        **kwargs
    )


@register.inclusion_tag(
    'creme_core/templatetags/bricks/menu-action.html',
    takes_context=True,
)
def brick_menu_collapse_action(context, state):
    return _brick_menu_state_action(
        context,
        action_id='collapse',
        current_state=state.is_open,
        in_label=_('Collapse block'), out_label=_('Expand block'),
    )


@register.inclusion_tag(
    'creme_core/templatetags/bricks/menu-action.html',
    takes_context=True,
)
def brick_menu_reduce_action(context, state):
    return _brick_menu_state_action(
        context,
        action_id='reduce-content',
        current_state=state.show_empty_fields,
        in_label=_('Hide empty fields'), out_label=_('Show empty fields'),
    )


# TODO: attrs => only 'class' ?
@register.inclusion_tag('creme_core/templatetags/bricks/table-column.html')
def brick_table_column(title, status='', **attrs):
    """Column header for table-bricks
    (ie: template which extends creme_core/bricks/base/table.html or
    creme_core/bricks/base/paginated-table.html, or which contains a <table>).

    @param title: Title of the column (string).
    @param status: String use to tag the HTML node. Classical ones: 'primary', 'action'.
    @param attrs: keywords arguments are serialized to HTML attributes.
           Beware: '_' are replaced by '-'.

    Example:
        {% extends 'creme_core/bricks/base/table.html' %}
        {% load i18n creme_bricks %}

        ....

        {% block brick_table_columns %}
            {% brick_table_column title=_('Name') status='primary' %}
            {% brick_table_column title=_('Information') %}
            {% brick_table_column title=_('Action') status='action' %}
        {% endblock %}

        ...
    """
    return {
        'title':      title,
        'status':     status.split(' ') if status else (),
        'attributes': mark_safe(
            ' '.join(
                '{}="{}"'.format(k.replace('_', '-'), v)
                for k, v in attrs.items()
            )
        ),
    }


# TODO: attrs => only 'class' & 'colspan' ? (+ 'ATTR:colspan' ?)
@register.inclusion_tag(
    'creme_core/templatetags/bricks/table-column.html',
    takes_context=True,
)
def brick_table_column_for_cell(context, cell, title='', status='', **attrs):
    """Column header for table-bricks (see brick_table_column()) related to an EntityCell.

    @param context: Template context.
    @param cell: Instance of EntityCellRegularField
           (tips: you can use the templatetag lib 'creme_cells').
    @param title: Title of the column (string). By default, the cell's title is used.
    @param status: String use to tag the HTML node. Classical ones: 'primary', 'action'.
    @param attrs: keywords arguments are serialized to HTML attributes.
           Beware: '_' are replaced by '-'.
    """
    assert isinstance(cell, EntityCellRegularField)

    sort_data = None
    help = ''
    verbose_name = title or cell.title

    # TODO: only if the brick manages sorting (QuerysetBrick) ??
    # TODO: take the registry from the context ? the arguments ?
    # if cell.sortable:
    if sorter.cell_sorter_registry.get_field_name(cell):
        current_sort = context.get('order_by')

        if current_sort:
            current_is_desc = current_sort.startswith('-')
            current_field = current_sort[1:] if current_is_desc else current_sort

            field_name = cell.value
            sort_data = {
                'sorted': field_name == current_field,
                'field': field_name,
                'order': 'desc' if current_is_desc else 'asc',  # TODO: use utils.meta.Order
            }
            help = _('Sort «{model}» by «{field}»').format(
                model=cell.model._meta.verbose_name_plural,
                field=verbose_name,
            )

    if 'data_type' not in attrs:
        data_type = cell.data_type

        if data_type:
            attrs['data_type'] = data_type

    return {
        'title':      verbose_name,
        'key':        cell.key,
        'help':       help,
        'sort_by':    sort_data,
        'status':     status.split(' ') if status else (),
        'attributes': mark_safe(
            ' '.join('{}="{}"'.format(k.replace('_', '-'), v) for k, v in attrs.items())
        ),
    }


@register.inclusion_tag(
    'creme_core/templatetags/bricks/table-column.html',
    takes_context=True,
)
def brick_table_column_for_field(context, ctype, field, title='', status='', **attrs):
    """Column header for table-bricks (see brick_table_column()) related to a model field.

    @param context: Template context.
    @param ctype: Instance of ContentType. Tips:
           - you can use the templatetag lib 'creme_ctype'.
           - QuerysetBrick fill the template variable 'objects_ctype'.
    @param field: Name of the field (string).
    @param title: Title of the column (string). By default, the field's verbose name is used.
    @param status: String use to tag the HTML node. Classical ones: 'primary', 'action'.
    @param attrs: keywords arguments are serialized to HTML attributes.

    Example:
      {% extends 'creme_core/bricks/base/paginated-table.html' %}
      {% load i18n creme_bricks %}

      ...

      {% block brick_table_columns %}
        {% brick_table_column_for_field ctype=objects_ctype field='name' status='primary' %}
        {% brick_table_column_for_field ctype=objects_ctype field='status' title=_('My status') %}
        {% brick_table_column_for_field ctype=objects_ctype field='info' %}
      {% endblock %}

      ...
    """
    cell = EntityCellRegularField.build(ctype.model_class(), field)

    if cell is None:
        raise ValueError(f'Invalid field (ctype={ctype}, field="{field}")')

    return brick_table_column_for_cell(context, cell=cell, title=title, status=status, **attrs)


@register.inclusion_tag(
    'creme_core/templatetags/bricks/table-action.html',
    takes_context=True,
)
def brick_table_action(context, id, **kwargs):
    """Action
    (see brick_brick_action()) for the content of a table-brick (see brick_table_column()).

    Example:
        {% extends 'creme_core/bricks/base/paginated-table.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_table_rows %}
            {% for object in page.object_list %}
            <tr>
                <td>...</td>
                <td>...</td>
                <td {% brick_table_data_status action %}>
                    {% brick_table_action id='edit' url=object.get_edit_absolute_url
                                          label=_('Edit this stuff') enabled=has_perm %}
                </td>
            </tr>
            {% endfor %}
        {% endblock %}

        ...
    """
    return brick_action(context, id=id, **kwargs)


@register.tag
def brick_table_data_status(parser, token):
    """Mark some <td> in table-bricks with specific HTML attribute.

    Generally markers are 'primary' and 'action', but you can use your own.

    Example:
        {% extends 'creme_core/bricks/base/table.html' %}
        {% load creme_bricks %}

        ...

        {% block brick_table_rows %}
            <tr>
                {# Will have "data-table-primary-column" attribute #}
                <td {% brick_table_data_status primary %}> ... </td>
                ...
            </tr>
        {% endblock %}
    """
    tokens = token.split_contents()  # Splitting by None == splitting by spaces.

    if len(tokens) < 2:
        raise TemplateSyntaxError(f'"{tokens[0]}" tag requires at least one argument.')

    return TextNode(' '.join(f'data-table-{t}-column' for t in tokens[1:]))


@register.simple_tag
def brick_state_classes(state):
    classes = []

    if not state.is_open:
        classes.append('is-collapsed')

    if not state.show_empty_fields:
        classes.append('is-content-reduced')

    return ' '.join(classes)


@register.inclusion_tag(
    'creme_core/templatetags/bricks/tile-action.html',
    takes_context=True,
)
def brick_tile_action(context, id, **kwargs):
    """Action (see brick_action()) for the content of a tiles-brick
    (see creme/creme_core/templates/creme_core/bricks/base/tiles.html).

    Example:
        {% extends 'creme_core/bricks/base/tiles.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_content %}
            {% for object in objects %}
            <div class="brick-tile">
                <span class="brick-tile-value">
                    ...
                </span>
                <span class="brick-tile-name">
                    {% url 'my_app__remove_stuff' object.id as remove_url %}
                    {% brick_tile_action id='delete' url=remove_url
                         __id=object.id type='unlink' label=_('Remove this stuff') %}
                </span>
            </div>
            {% endfor %}
        {% endblock %}
    """
    return brick_action(context, id=id, **kwargs)


@register.inclusion_tag('creme_core/templatetags/bricks/tile.html')
def brick_tile(label, value, multiline=False, data_type=None):
    """Tile (displaying a label & a value) for tiles-brick
    (see creme/creme_core/templates/creme_core/bricks/base/tiles.html).

    @param label: String.
    @param value: Value associated to this label.
    @param multiline: If True, the tile will have the attribute "brick-tile-multiline-value"
           (so multi-line tiles can be managed differently by CSS).
    @param data_type: String.
           Available values are in creme_core.core.entity_cell.FIELDS_DATA_TYPES.

    Example:
        {% extends 'creme_core/bricks/base/tiles.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_content %}
            {% brick_tile label=_('Name') value=my_name %}
            ...
        {% endblock %}
    """
    return {
        'label': label,
        'content': value,
        'multiline': multiline,
        'data_type': data_type,
    }


@register.inclusion_tag('creme_core/templatetags/bricks/tile.html')
def brick_tile_for_cell(cell, instance, user):  # TODO: keywords only ?
    """Tile for tiles-brick (see creme/creme_core/templates/creme_core/bricks/base/tiles.html)
    related to an EntityCell, for a given instance.
    The tile will display the cell's title as label, the cell's value (for the instance) ;
    if the cell can be inner-edited, an action will be automatically created.

    @param cell: Instance of EntityCell (tips: use the templatetag lib 'creme_cells').
    @param instance: Instance of model. The EntityCell must be related to this model of course.
    @param user: Instance of auth.get_user_model(). Used to check credentials.

    Example:
        {% extends 'creme_core/bricks/base/tiles.html' %}
        {% load i18n creme_bricks creme_cells %}

        ...

        {% block brick_content %}
            {% cell_4_regularfield instance=my_instance field='name' as name_cell %}
            {% brick_tile_for_cell cell=name_cell instance=my_instance  user=user %}
            ...
        {% endblock %}
    """
    try:
        content = cell.render_html(instance, user)
    except Exception:
        logger.exception('Error when rendering cell in {% brick_tile_for_cell %}')
        content = ''

    return {
        'key':   cell.key,
        'label': cell.title,

        'content':   mark_safe(content),
        'data_type': cell.data_type,
        'multiline': cell.is_multiline,

        # TODO: pass the registry in context ?
        'edit_url':  bulk_update.bulk_update_registry.inner_uri(
            cell=cell, instance=instance, user=user,
        ),
        'edit_perm': _bulk_has_perm(instance, user),
    }


@register.inclusion_tag(
    'creme_core/templatetags/bricks/card-action.html',
    takes_context=True,
)
def brick_card_action(context, url, enabled, id='edit', display='both', **kwargs):
    """Action (see brick_action()) for the content of a hat-card-brick
    (see creme/creme_core/templates/creme_core/bricks/base/hat-card.html).

    Example:
        {% extends 'creme_core/bricks/base/hat-card.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block card_fields %}
            <div class="card-info-field">
                <span class='card-info-key'>{% translate 'My label' %}</span>
                <span class='card-info-value'>
                    {{my_value}}
                    {% brick_card_action url=my_url enabled=True %}
                </span>
            </div>

            ...
        {% endblock %}
    """
    return brick_action(
        context,
        id=id,
        url=url,
        enabled=enabled,
        display=display,
        **kwargs
    )


# TODO: use a brick_card_action_for_cell tag ??
@register.inclusion_tag(
    'creme_core/templatetags/bricks/card-action.html',
    takes_context=True,
)
def brick_card_action_for_field(context, instance, field, user, **kwargs):
    """Inner-edition action (see brick_action()) for a field in a hat-card-brick
    (see creme/creme_core/templates/creme_core/bricks/base/hat-card.html).

    Example:
        {% extends 'creme_core/bricks/base/hat-card.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block card_fields %}
            <div class="card-info-field">
                <span class='card-info-key'>{% translate 'My field' %}</span>
                <span class='card-info-value'>
                    {{object.my_field|default:'—'}}
                    {% brick_card_action_for_field instance=object field='my_field' user=user %}
                </span>
            </div>

            ...
        {% endblock %}
    """
    cell = EntityCellRegularField.build(type(instance), field)

    if cell is None:
        raise ValueError(f'Invalid field (instance={instance}, field="{field}")')

    # TODO: pass the registry in context ?
    return brick_card_action(
        context,
        url=bulk_update.bulk_update_registry.inner_uri(
            cell=cell, instance=instance, user=user,
        ),
        enabled=_bulk_has_perm(instance, user),
        **kwargs
    )


@register.inclusion_tag('creme_core/templatetags/bricks/pager.html')
def brick_pager(page):
    context = PagerContext(page)
    return {
        'links': context.links,
        'first': context.first,
        'last': context.last,
    }


@register.simple_tag(takes_context=True)
def brick_import(context, app=None, name=None, object=None):
    """ Import an instance of a registered Brick.

    Can be used in 2 ways.

    1. Import a Brick by its name.

        my_app/bricks.py :
            from creme.creme_core.gui.bricks import Brick

            class MyBrick(Brick):
                # Beware to the ID: app-label + name
                id_ = Brick.generate_id('my_app', 'my_brick')

                [...]

        my_app/app.py
            from creme.creme_core.apps import CremeAppConfig

            class MyAppConfig(CremeAppConfig):
                name = 'creme.my_app'
                verbose_name = 'My app'

                def register_bricks(self, brick_registry):
                    from . import bricks

                    brick_registry.register(bricks.MyBrick)  # <== Registration is mandatory

                [...]

        my_app/templates/my_app/my_template.html
            {% load creme_bricks %}

            {% brick_import app='my_app' name='my_brick' as my_brick_instance %}
            {# See {% brick_display ... %}  to display this instance #}

    2. Import the 'object' Brick for a specific instance.

       By default, this Brick will display all the visible fields of this instance ;
       but you can customise this Brick (see BrickRegistry.register_4_model()).

       {% brick_import object=object as object_brick %}
    """
    if object is not None:
        if app is not None or name is not None:
            raise TemplateSyntaxError(
                '{% brick_import %}: if you give "object" parameter, '
                'you cannot give app/name parameters.'
            )

        brick = bricks.brick_registry.get_brick_4_object(object)
    else:
        if app is None or name is None:
            raise TemplateSyntaxError(
                '{% brick_import %}: you have to give "app" AND "name" parameters.'
            )

        brick = bricks.brick_registry[Brick.generate_id(app, name)]()

    BricksManager.get(context).add_group(brick.id_, brick)

    return brick


@register.simple_tag(takes_context=True)
def brick_declare(context, *bricks):
    """ Declare some instances of Brick which have been injected in the
    template context.

    When you have a view which builds its own instances of Bricks & inject them
    in the template context, you don't import them with {% brick_import %}, but
    you have to declare anyway, so they are known by the current BricksManager
    (it's used to regroup queries about Bricks states).

    my_app/views.py
        [...]

        def my_view(request):
            return render(
                request, 'my_app/foo.html',
                {
                    # Here we inject a list od instances.
                    'my_bricks': [MyBrick1(), MyBrick2()],

                    # Here we inject a simple instance.
                    'my_brick3': MyBrick3(),

                    # Example of reloading view.
                    'bricks_reload_url': reverse('creme_core__reload_bricks'),
                },
            )

    my_app/templates/my_app/my_template.html
        {% load creme_bricks %}

        {% brick_declare my_bricks my_brick3 %}
        {# See {% brick_display ... %}  to display this instance #}
    """
    add_group = BricksManager.get(context).add_group

    for brick_or_seq in bricks:
        if brick_or_seq == '':
            raise ValueError(
                '{% brick_declare %}, "bricks" seems empty. Is you variable valid ?'
            )

        if hasattr(brick_or_seq, '__iter__'):
            for brick in brick_or_seq:
                add_group(brick.id_, brick)
        else:
            add_group(brick_or_seq.id_, brick_or_seq)

    return ''


@register.simple_tag
def brick_get_by_ids(*brick_ids, **kwargs):
    """ Get a list of instances of registered Brick, from a list of brick IDs.
    It's useful to get information on a Brick when we only get it's ID
    (eg: it's stored in an instance of BrickHomeLocation).

        {% load creme_bricks %}

        {% brick_get_by_ids brick_id1 brick_id2 as bricks %}
        <span>{{bricks.0.verbose_name}}</span>

    An instance of CremeEntity can be given to retrieve correctly EntityBricks
    (even if this case is not currently used in Creme...) :

        {% brick_get_by_ids brick_id1 brick_id2 entity=my_instance as bricks %}
    """
    return [*bricks.brick_registry.get_bricks(brick_ids, entity=kwargs.get('entity'))]


_DISPLAY_METHODS = {
    'detail': 'detailview_display',
    'home':   'home_display',
}


@register.simple_tag(takes_context=True)
def brick_display(context, *bricks, **kwargs):
    """ Display some Brick instances.

    Note: see {% brick_import %} & {% brick_declare %} on how to get Bricks
    instances in your context.

        {% load creme_bricks %}

        [...]

        {% brick_display my_brick1 my_brick2 %}

    By default, the method detailview_display() of the bricks is called ;
    but you can call the different render method by giving the keyword argument 'render':

        {% brick_display my_brick1 my_brick2 render='home' %}

    Possible values are:
       - 'detail'  => detailview_display() (default value)
       - 'home'    => home_display()
    """
    context_dict = context.flatten()
    render_type = kwargs.get('render', 'detail')

    try:
        brick_render_method = _DISPLAY_METHODS[render_type]
    except KeyError as e:
        raise ValueError(
            '{{% brick_display %}}: "render" argument must be in [{}].'.format(
                ', '.join(_DISPLAY_METHODS.keys())
            )
        ) from e

    def render(brick):
        fun = getattr(brick, brick_render_method, None)

        if fun:
            # NB: the context is copied is order to a 'fresh' one for each brick,
            #     & so avoid annoying side-effects.
            return fun({**context_dict})

        logger.warning(
            'Brick without %s(): %s (id=%s)',
            brick_render_method, brick.__class__, brick.id_,
        )

    bricks_to_render = []

    def pop_group(brick_id):
        try:
            BricksManager.get(context).pop_group(brick_id)
        except KeyError as e:
            raise ValueError(
                '{{% brick_display %}}: it seems that this brick has not been '
                f'declared/imported: {brick_id}'
            ) from e

    for brick_or_seq in bricks:
        if brick_or_seq == '':
            raise ValueError(
                '{% brick_display %}: "bricks" seems empty. Is you variable valid ?'
            )

        # We avoid generator, because we need to iterate twice (import & display)
        if isinstance(brick_or_seq, (list, tuple)):
            for brick in brick_or_seq:
                pop_group(brick.id_)
                bricks_to_render.append(brick)
        else:
            pop_group(brick_or_seq.id_)
            bricks_to_render.append(brick_or_seq)

    return mark_safe(''.join(filter(
        None,
        (render(brick) for brick in bricks_to_render)
    )))


@register.simple_tag(takes_context=True)
def brick_end(context):
    """You should use this tag in every view which uses some bricks,
    after all Bricks have been displayed.
    """
    bricks_manager = BricksManager.get(context)

    res = ''
    remaining_groups = bricks_manager.get_remaining_groups()

    if remaining_groups:
        res = """
<div>
    BEWARE ! There are some unused imported bricks.
    <ul>{}</ul>
</div>""".format(''.join(f'<li>{group}</li>' for group in remaining_groups))

    return mark_safe(res)
