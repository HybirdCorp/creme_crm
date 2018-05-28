# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from datetime import date, time
from decimal import Decimal
# from functools import partial
from json import dumps as json_dump
import logging
# import warnings

# from django.contrib.contenttypes.models import ContentType
# from django.core.urlresolvers import reverse
from django.template import Library, TemplateSyntaxError
from django.template.base import TextNode
# from django.utils.functional import Promise
from django.utils.safestring import mark_safe, SafeData
from django.utils.translation import ugettext as _, ugettext_lazy

from ..core.entity_cell import EntityCellRegularField  # EntityCellCustomField
from ..gui.bricks import Brick, brick_registry, BricksManager
from ..gui.bulk_update import bulk_update_registry
from ..gui.pager import PagerContext
from ..utils.media import get_current_theme_from_context
from ..utils.translation import plural as is_plural
from ..views.bricks import render_detailview_brick, render_home_brick  # render_portal_brick
from ..views.entity import _bulk_has_perm

from .creme_widgets import get_icon_size_px, get_icon_by_name


register = Library()
logger = logging.getLogger(__name__)


# TODO: 'selection_title' really need to be hard coded ? kwargs + html attr instead ?
#       (generate an 'indicator' as loading => merge this concepts ??)
@register.inclusion_tag('creme_core/templatetags/bricks/title.html', takes_context=True)
def brick_header_title(context, title, plural=None, empty=None, icon='info', count=None, selection_title=None, selection_plural=None):
    """Display the title of a brick.
    Should be used in the template block 'brick_header_title'.

    @param title: Title of the brick. If you want to display a number of items (eg: number of lines in this brick)
                  & so pluralize the title, use a format variable '{count}' and the parameter 'plural'.
    @param plural: Title to use with a plural number of items. If you set it, it must use format variable '{count}'
                   & the parameter 'title' too.
    @param empty: Title to use it there no items in the bricks.
    @param icon: The string identifying an Icon (eg: 'add'), or an Icon instance
                 (see the templatetag {% widget_icon  %} of the lib creme_widget.
                 Default is 'info' icon.
    @param count: Number of items in the bricks. If you don't set it, & the brick is paginated, the paginator's count is used.
    @param selection_title: Additional text displayed in title of bricks which allow to select items.
                            The related brick must have the class 'brick-selectable' & a column
                            with class 'data-selectable-selector-column'.
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
            {% brick_header_title title=_('{count} Customers') plural=_('{count} Customers') empty=_('Customers') icon='phone' %}
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

    if isinstance(icon, basestring):
        # TODO: cache ?
        theme = get_current_theme_from_context(context)
        icon = get_icon_by_name(icon, theme, size_px=get_icon_size_px(theme, size='brick-header'),
                                label=_(u'Information') if icon == 'info' else rendered_title,
                               )

    return {
        'title': rendered_title,
        'icon': icon,
        'selection_title': selection_title,
        'selection_plural': selection_plural,
    }


DEFAULT_ACTION_LABELS = {
    'edit':   ugettext_lazy(u'Edit'),
    'delete': ugettext_lazy(u'Delete'),
}

_DISPLAY_VALUES = frozenset(('text', 'icon', 'both'))


@register.inclusion_tag('creme_core/templatetags/bricks/action.html', takes_context=True)
def brick_action(context, id, url='', label='', icon=None, icon_size='brick-action', display='icon', enabled=True,
                 confirm=None, loading=None, **kwargs):
    """Create a Creme-action (ie: link/button related to JavaScript code) made for use in a brick
    (see  creme/creme_core/static/creme_core/js/bricks.js).

    This kind of action will reload the brick (& its dependencies) when it's needed.
    There are more specialised templatetags (wrappers) for specific context (brick header, table-brick):
      {% brick_header_action .. %}, {% brick_table_action ... %}...

    @param id: ID of the action. An ID 'foo-bar' will correspond to the method '_action_foo_bar' of the brick.
           Description of the actions defined by the core (some apps define their own actions, bind to their own bricks):
            - add: displays an inner-popup designed to contains a form. Only need the parameter 'url' to be filled.
            - edit: idem.
            - link: idem.
            - add-relationships: displays a list-view in an inner-popup, & creates Relations with selected entities.
                The 'url' parameter is ignored, but the following data must be provided:
                    __subject_id: ID of the <subject> entity.
                    __rtype_id: ID of the used RelationType.
                    __ctype_id: ID of the ContentType of the <object> entities (which are selected by the user).
                This data is optional:
                     __multiple: True means 'multi-selection'.
                TODO: automatically use icon='link'.
            - delete: sends a POST request data to the given 'url', using action's data (see kwargs) as POST data.
                      The user has to confirm (a default confirmation message is provided if it's not set).
            - update: sends a POST request data to the given 'url', using action's data (see kwargs) as POST data.
            - update-redirect: idem as 'update', but the page is redirected with the URL sent by the server in its response.
            - view: displays an inner-popup designed to contains an HTML fragment.
                    You have to fill the parameter 'url'.
                    The extra data '__title' is optional (title of the inner-popup).
            - redirect: redirect the page to the given 'url'.
            - refresh: reload the brick & its dependencies (internal use)
    @param url: URL (string) used by the action (creation, edition etc...).
           Most of the actions need the URL to be given (see 'id' documentation).
    @param label: String. Default labels are available for some action IDs (see DEFAULT_ACTION_LABELS).
    @param icon: The string identifying an Icon (eg: 'add'), or an Icon instance
           (see the templatetag {% widget_icon  %} of the lib creme_widget).
           Default is None ; but when an icon is need (parameter 'display' is 'icon or 'both') but no 'icon' is given,
           the parameter 'type' & 'id' are used as icon name (so actions like 'add' use a default icon).
    @param icon_size: Size-tag (see creme/creme_core/gui/icons.py -> _ICON_SIZES_MAP).
           Only useful if you pass a string as 'icon' parameter.
           Default is 'brick-action'.
           Notice that wrappers (brick_header_action, brick_table_action etc...) will pass a correct size for them.
    @param display: String in {'text', 'icon', 'both'} ('both' means 'text' AND 'icon'}.
           Default is 'icon' (but wrappers can override this default value).
    @param enabled: Boolean indicating if the action must be active (generally used for with credentials check).
           Default is True.
    @param confirm: Confirmation message. A not empty message means that a confirmation popup is displayed with this message.
           Default is None.
    @param loading: Loading message.
    @param kwargs:
           These keys have a precise meaning:
                - 'type': String used to generate the CSS class "action-type-{{action_type}}" ;
                          classical provided types are the actions IDs (add, edit...)
                - 'class': Extra CSS class.
           Remaining keys must start with '__' ; they are serialised to JSON & can be used by the code of the action.
    """
    assert display in _DISPLAY_VALUES

    action_type = kwargs.pop('type', id)
    css_class   = kwargs.pop('class', '')
    properties = []

    if icon is None and display != 'text':
        icon = action_type

    if not label:
        label = DEFAULT_ACTION_LABELS.get(action_type, '')

    if isinstance(icon, basestring):
        theme = get_current_theme_from_context(context)
        icon = get_icon_by_name(icon, theme, size_px=get_icon_size_px(theme, icon_size),
                                label=_(u'Information') if icon == 'info' else label,
                               )

    # TODO: factorise with utils
    def _jsonify(value):
        if isinstance(value, (date, time)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return float(value)

        # if isinstance(value, Promise):
        #     return unicode(value)
        #
        # raise TypeError("%s is not JSON serializable" % type(value))
        return unicode(value)

    def _clean_extra_data(data, prefix='__'):
        prefix_length = len(prefix)
        extra_data = {}

        # return {key[prefix_length:]: value
        #             for key, value in data.iteritems()
        #                 if key.startswith(prefix)
        # }
        for key, value in data.iteritems():
            if not key.startswith(prefix):
                raise TemplateSyntaxError('The key "{}" does not starts with {}'.format(key, prefix))

            extra_data[key[prefix_length:]] = value

        return extra_data

    if not enabled:
        properties.append('is-disabled')

    if loading:
        properties.append('is-async-action')

    return {
        'url':      url,
        'disabled': not enabled,

        'label':   label,
        'icon':    icon,
        'display': display,

        'action_id':   id,
        'action_type': action_type,

        'properties': ' '.join(properties),
        'class':      css_class,
        'loading':    bool(loading),

        'data': mark_safe(json_dump({'options': {
                                          'confirm': confirm,
                                          'loading': None if loading is True else loading,
                                     },
                                     'data': _clean_extra_data(kwargs),
                                    },
                                    default=_jsonify,
                                   )
                         ),
    }


@register.inclusion_tag('creme_core/templatetags/bricks/header-action.html', takes_context=True)
def brick_header_action(context, display='both', **kwargs):
    """Action (see brick_brick_action()) for brick's header.

    Example:
        {% extends 'creme_core/bricks/base/base.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_header_actions %}
            {% brick_header_action id='add' url=creation_url label=_('Add a stuff') enabled=can_create_stuff %}
        {% endblock %}

        ...
    """
    return brick_action(context, display=display, **kwargs)


@register.inclusion_tag('creme_core/templatetags/bricks/card-button.html', takes_context=True)
def brick_card_button(context, action, url, label, icon=None, enabled=True, confirm=None, **kwargs):
    """Action (see brick_brick_action()) for "card" (hat) bricks.

    Notice that the size of instanced Icons should be "brick-hat-card-button".
    """
    return brick_action(context, id=action, url=url, label=label, icon=icon, icon_size='brick-hat-card-button',
                        enabled=enabled, confirm=confirm,
                        **kwargs
                       )


@register.inclusion_tag('creme_core/templatetags/bricks/bar-button.html', takes_context=True)
def brick_bar_button(context, action, url, label, icon, enabled=True, confirm=None, **kwargs):
    """Action (see brick_brick_action()) for "bar" (hat) bricks.

    Notice that the size of instanced Icons should be "brick-hat-bar-button".
    """
    return brick_action(context, id=action, url=url, label=label, icon=icon, icon_size='brick-hat-bar-button',
                        enabled=enabled, confirm=confirm,
                        **kwargs
                       )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def brick_menu_action(context, id, **kwargs):
    """Action (see brick_brick_action()) for the (hidden menu) of a brick.

    Example:
        {% extends 'creme_core/bricks/base/base.html' %}
        {% load i18n creme_core_tags creme_bricks %}

        ...

        {% block brick_menu_actions %}
            {{block.super}}

            <hr/>
            {% brick_menu_action id='edit' url=config_url icon='config' label=_('Configure the block') enabled=config_perm %}
        {% endblock %}

        ...
    """
    return brick_action(context, id=id, icon_size='brick-menu-action', **kwargs)


def _brick_menu_state_action(context, action_id, current_state, in_label, out_label, icon='view_less', **kwargs):
    return brick_action(context, id=action_id,
                        icon=icon,
                        label=in_label if current_state else out_label,
                        __inlabel=in_label,
                        __outlabel=out_label,
                        **kwargs
                       )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def brick_menu_collapse_action(context, state):
    return _brick_menu_state_action(context, action_id='collapse',
                                    current_state=state.is_open,
                                    in_label=_(u'Collapse block'), out_label=_(u'Expand block'),
                                   )


@register.inclusion_tag('creme_core/templatetags/bricks/menu-action.html', takes_context=True)
def brick_menu_reduce_action(context, state):
    return _brick_menu_state_action(context, action_id='reduce-content',
                                    current_state=state.show_empty_fields,
                                    in_label=_(u'Hide empty fields'), out_label=_(u'Show empty fields'),
                                   )


# TODO: attrs => only 'class' ?
@register.inclusion_tag('creme_core/templatetags/bricks/table-column.html')
def brick_table_column(title, status='', **attrs):
    """Column header for table-bricks (ie template which extends creme_core/bricks/base/table.html or
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
        'attributes': mark_safe(' '.join('{}="{}"'.format(k.replace('_', '-'), v) for k, v in attrs.iteritems())),
    }


# TODO: attrs => only 'class' & 'colspan' ? (+ 'ATTR:colspan' ?)
@register.inclusion_tag('creme_core/templatetags/bricks/table-column.html', takes_context=True)
def brick_table_column_for_cell(context, cell, title='', status='', **attrs):
    """Column header for table-bricks (see brick_table_column()) related to an EntityCell.

    @param cell: Instance of EntityCellRegularField (tips: you can use the templatetag lib 'creme_cells').
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
    if cell.sortable:
        current_sort = context.get('order_by')

        if current_sort:
            current_is_desc = current_sort.startswith('-')
            current_field = current_sort[1:] if current_is_desc else current_sort

            field_name = cell.value
            sort_data = {
                'sorted': field_name == current_field,
                'field': field_name,
                'order': 'desc' if current_is_desc else 'asc',
            }
            help = _(u'Sort «{model}» by «{field}»').format(model=cell.model._meta.verbose_name_plural,
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
        'attributes': mark_safe(' '.join('{}="{}"'.format(k.replace('_', '-'), v) for k, v in attrs.iteritems())),
    }


@register.inclusion_tag('creme_core/templatetags/bricks/table-column.html', takes_context=True)
def brick_table_column_for_field(context, ctype, field, title='', status='', **attrs):
    """Column header for table-bricks (see brick_table_column()) related to a model field.

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
        raise ValueError('Invalid field (ctype=%s, field="%s")' % (ctype, field))

    return brick_table_column_for_cell(context, cell=cell, title=title, status=status, **attrs)


@register.inclusion_tag('creme_core/templatetags/bricks/table-action.html', takes_context=True)
def brick_table_action(context, id, **kwargs):
    """Action (see brick_brick_action()) for the content of a table-brick (see brick_table_column()).

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
                    {% brick_table_action id='edit' url=object.get_edit_absolute_url label=_('Edit this stuff') enabled=has_perm %}
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
                <td {% brick_table_data_status primary %}> ... </td> {# Will have "data-table-primary-column" attribute #}
                ...
            </tr>
        {% endblock %}
    """
    tokens = token.split_contents()  # Splitting by None == splitting by spaces.

    if len(tokens) < 2:
        raise TemplateSyntaxError('"%r" tag requires at least one argument.' % tokens[0])

    return TextNode(' '.join('data-table-%s-column' % t for t in tokens[1:]))


@register.simple_tag
def brick_state_classes(state):
    classes = []

    if not state.is_open:
        classes.append('is-collapsed')

    if not state.show_empty_fields:
        classes.append('is-content-reduced')

    return ' '.join(classes)


@register.inclusion_tag('creme_core/templatetags/bricks/tile-action.html', takes_context=True)
def brick_tile_action(context, id, **kwargs):
    """Action (see brick_brick_action()) for the content of a tiles-brick
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
                    {% brick_tile_action id='delete' url=remove_url __id=object.id type='unlink' label=_('Remove this stuff') %}
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
    @param data_type: String. See available values in creme/creme_core/core/entity_cell.py -> FIELDS_DATA_TYPES.

    Example:
        {% extends 'creme_core/bricks/base/tiles.html' %}
        {% load i18n creme_bricks %}

        ...

        {% block brick_content %}
            {% brick_tile label=_('Name') value=my_name %}
            ...
        {% endblock %}
    """
    return {'label': label,
            'content': value,
            'multiline': multiline,
            'data_type': data_type,
           }


@register.inclusion_tag('creme_core/templatetags/bricks/tile.html')
def brick_tile_for_cell(cell, instance, user):
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
    # edit_url = None
    #
    # if isinstance(cell, EntityCellRegularField):
    #     field_name = cell.field_info[0].name
    #
    #     if bulk_update_registry.is_updatable(instance.__class__, field_name, exclude_unique=False):
    #         ct = ContentType.objects.get_for_model(instance.__class__)
    #         edit_url = reverse('creme_core__inner_edition', args=(ct.id, instance.id, field_name))
    #
    # elif isinstance(cell, EntityCellCustomField):
    #     edit_url = reverse('creme_core__inner_edition',
    #                        args=(instance.entity_type_id, instance.id, 'customfield-%s' % cell.value),
    #                       )

    try:
        content = cell.render_html(instance, user)
    except:
        logger.exception('Error when rendering cell in {% brick_tile_for_cell %}')
        content = ''

    return {
        'key':   cell.key,
        'label': cell.title,

        'content':   mark_safe(content),
        'data_type': cell.data_type,
        'multiline': cell.is_multiline,

        # 'edit_url':  edit_url,
        'edit_url':  bulk_update_registry.inner_uri(cell=cell, instance=instance, user=user),
        'edit_perm': _bulk_has_perm(instance, user),
    }


@register.inclusion_tag('creme_core/templatetags/bricks/pager.html')
def brick_pager(page):
    context = PagerContext(page)
    return {
        'links': context.links,
        'first': context.first,
        'last': context.last,
    }


# @register.assignment_tag(takes_context=True)
@register.simple_tag(takes_context=True)
def brick_import(context, app=None, name=None, object=None):
    """ Import an instance of a registered Brick.

    Can be used in 2 ways.

    1. Import a Brick by its name.

        my_app/bricks.py :
            from creme.creme_core.gui.bricks import Brick

            class MyBrick(Brick):
                id_ = Brick.generate_id('my_app', 'my_brick')  # <== Beware to the ID: app-label + name

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
            raise TemplateSyntaxError('{% brick_import %}: if you give "object" parameter, you cannot give app/name parameters.')

        brick = brick_registry.get_brick_4_object(object)
    else:
        if app is None or name is None:
            raise TemplateSyntaxError('{% brick_import %}: you have to give "app" AND "name" parameters.')

        brick = brick_registry[Brick.generate_id(app, name)]()

    BricksManager.get(context).add_group(brick.id_, brick)

    return brick


@register.simple_tag(takes_context=True)
def brick_declare(context, *bricks):
    """ Declare some instances of Brick which have been injected in the template context.

    When you have a view which builds its own instances of Bricks & inject them in the template context,
    you don't import them with {% brick_import %}, but you have to declare anyway, so they are known by
    the current BricksManager (it's used to regroup queries about Bricks states).

    my_app/views.py
        [...]

        def my_view(request):
            return render(request, 'my_app/foo.html',
                          {'my_bricks': [MyBrick1(), MyBrick2()],  # <= Here we inject a list od instances.
                           'my_brick3': MyBrick3(),                # <= Here we inject a simple instance.

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
            raise ValueError('{% brick_declare %}, "bricks" seems empty. Is you variable valid ?')

        if hasattr(brick_or_seq, '__iter__'):
            for brick in brick_or_seq:
                add_group(brick.id_, brick)
        else:
            add_group(brick_or_seq.id_, brick_or_seq)

    return ''


@register.simple_tag(takes_context=True)
def brick_display(context, *bricks, **kwargs):
    """ Display some Brick instances.

    Note: see {% brick_import %} & {% brick_declare %} on how to get Bricks instances in your context.

        {% load creme_bricks %}

        [...]

        {% brick_display my_brick1 my_brick2 %}

    By default, the method detailview_display() of the bricks is called ; but you can call the different
    render method by giving the keyword argument 'render':

        {% brick_display my_brick1 my_brick2 render='home' %}

    Possible values are:
       - 'detail'  => detailview_display() (default value)
       - 'home'    => home_display()
    """
    context_dict = context.flatten()
    render_type = kwargs.get('render', 'detail')

    if render_type == 'detail':
        render = render_detailview_brick
    elif render_type == 'home':
        render = render_home_brick
    # elif render_type == 'portal':
    #     warnings.warn('''In {% brick_display %}, the option "render='portal'" is deprecated.''', DeprecationWarning)
    #     render = partial(render_portal_brick, ct_ids=context['ct_ids'])
    else:
        # raise ValueError('{% brick_display %}: "render" argument must be in {detail|home|portal}.')
        raise ValueError('{% brick_display %}: "render" argument must be in {detail|home}.')

    bricks_to_render = []

    def pop_group(brick_id):
        try:
            BricksManager.get(context).pop_group(brick_id)
        except KeyError:
            raise ValueError('{%% brick_display %%}: it seems that this brick has not been declared/imported: %s' % brick_id)

    for brick_or_seq in bricks:
        if brick_or_seq == '':
            raise ValueError('{% brick_display %}: "bricks" seems empty. Is you variable valid ?')

        # We avoid generator, because we need to iterate twice (import & display)
        if isinstance(brick_or_seq, (list, tuple)):
            for brick in brick_or_seq:
                pop_group(brick.id_)
                bricks_to_render.append(brick)
        else:
            pop_group(brick_or_seq.id_)
            bricks_to_render.append(brick_or_seq)

    # NB: the context is copied is order to a 'fresh' one for each brick, & so avoid annoying side-effects.
    return mark_safe(''.join(render(brick, context=dict(context_dict)) for brick in bricks_to_render))


@register.simple_tag(takes_context=True)
def brick_end(context):
    """You should use this tag in every view which uses some bricks,
    after all Bricks have been displayed.
    """
    bricks_manager = BricksManager.get(context)

#     res = """
# <script type='text/javascript'>
#     $(document).ready(function() {
#         creme.utils.blocks_deps = {
#             %s
#         };
#
#         creme.utils.getBlocksDeps = function(block_name) {
#             console.warn('creme.utils.getBlocksDeps() is deprecated.');
#             var deps = creme.utils.blocks_deps[block_name];
#
#             if (typeof(deps) === undefined) {
#                 deps = '';
#             }
#
#             return deps;
#         };
#     });
# </script>""" % (', '.join('"{}": "{}"'.format(brick_id, ','.join(brick_deps))
#                               for brick_id, brick_deps in bricks_manager.get_dependencies_map().iteritems()
#                          )
#                )
    res = ''
    remaining_groups = bricks_manager.get_remaining_groups()

    if remaining_groups:
        # res += """
        res = """
<div>
    BEWARE ! There are some unused imported bricks.
    <ul>{}</ul>
</div>""".format(''.join('<li>{}</li>'.format(group) for group in remaining_groups))

    return mark_safe(res)
