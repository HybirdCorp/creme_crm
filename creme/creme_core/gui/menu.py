# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from json import dumps as json_dump
import logging
import math
import warnings

# from django.apps import apps
# from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy as reverse
# from django.utils.encoding import smart_unicode
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import ugettext as _, ungettext, ugettext_lazy

from ..auth import build_creation_perm as cperm
from ..models import CremeEntity
from ..templatetags.creme_widgets import get_icon_size_px, get_icon_by_name
from ..utils.media import get_current_theme_from_context
from ..utils.unicode_collation import collator


logger = logging.getLogger(__name__)


# if settings.OLD_MENU:
#     warnings.warn('The old menu API (settings.OLD_MENU = True) is deprecated.',
#                   DeprecationWarning
#                  )
#
#     # ---------------- Old Menu API --------------------------------------------
#     class MenuItem(object):
#         __slots__ = ('url', 'name', 'perm')
#
#         def __init__(self, url, name, perm):
#             self.url  = url
#             self.name = name
#             self.perm = perm
#
#         def __unicode__(self):
#             return u'<MenuItem: name:%s url:%s perm:%s>' % (self.url, self.name, self.perm)
#
#
#     class MenuAppItem(object):
#         def __init__(self, app_name, app_url, verbose_name=None, force_order=None):
#             """@param force_order Order of the item in the menu ; None if the verbose_name is use as key."""
#             self.app_name = app_name
#             self.app_url = app_url
#             self.name = verbose_name or apps.get_app_config(app_name).verbose_name
#             self.force_order = force_order
#             self._items = []
#
#         def __unicode__(self):
#             return u'<MenuAppItem: app:%s url:%s name:%s>' % (self.app_name, self.app_url, self.name)
#
#         def __iter__(self):
#             return iter(self._items)
#
#         items = property(lambda self: self._items)
#
#         def register_item(self, url, name, perm):
#             """
#             @param name Label used in the GUI ; using ugettext_lazy returned object is advised.
#             @param perm Permission string ; eg:'persons.add_organisation'
#             """
#             self.items.append(MenuItem(url, name, perm))
#
#
#     class CremeMenu(object):
#         def __init__(self):
#             self._app_items = {}
#
#         def __iter__(self):
#             return self._app_items.itervalues()
#
#         def get_app_item(self, app_name):
#             app_item = self._app_items.get(app_name)
#
#             if not app_item:
#                 raise KeyError('App not (yet) registered : %s (beware to the order for INSTALLED_APPS in settings.py)', app_name)
#
#             return app_item
#
#         def get_item_name(self, item_url):
#             for app_item in self._app_items.itervalues():
#                 for item in app_item:
#                     if smart_unicode(item.url) == smart_unicode(item_url):  # TODO: smart_unicode useful ???
#                         return item.name
#
#             return ''  # TODO: None ? exception ??
#
#         def register_app(self, app_name, app_url, name=None, force_order=None):
#             """@param force_order Order of the item in the menu ; None if the verbose_name is use as key."""
#             if not self._app_items.has_key(app_name):
#                 app_item = MenuAppItem(app_name, app_url, name, force_order)
#                 self._app_items[app_name] = app_item
#             else:
#                 logger.warn('This app has already been registered in the menu: %s', app_name)
#                 app_item = None
#
#             return app_item
#
#
#     creme_menu = CremeMenu()
# else:
def _validate_id(id_):
    if '"' in id_ or "'" in id_:
        raise ValueError("""ID cannot contain <"'> characters.""")

    return id_


class Item:
    def __init__(self, id):
        self.id = _validate_id(id)
        self._priority = None

    @property
    def priority(self):
        "Priority inside its container (see ItemList)"
        return self._priority

    def render(self, context, level=0):
        """Render as HTML.

        @param context: Context of the Template where the Item is rendered (dictionary).
                        We probably need theme name etc...
        @param level: Integer indicating the level of depth is the menu ; 0 is first, 1 is second.
        @return: HTML string.
        """
        raise NotImplementedError


class ViewableItem(Item):
    def __init__(self, id, label='', icon=None, icon_label='', perm=None):
        """
        @param id: Identifier (string). Must be unique in a container. A good way is to prefix with app label + '-'.
        @param label: Text displayed for this entry (should be a ugettext_lazy or something like that).
        @param icon: Icon identifier (string -- see icon system). Size used is 'brick-header'.
        @param icon_label: Label of the related icon (not used if 'icon' is None).
        @param perm: Permission (a not allowed entry will be disabled). Can be a classical permission string
               (eg: 'persons', 'persons.add_contact') or a callable which takes one argument (user) & returns
               a boolean.
        """
        super(ViewableItem, self).__init__(id)
        # TODO: assert there is at least an icon or a label ????
        self.label = label
        self.icon = icon
        self.icon_label = icon_label or label
        self.perm = perm

    # def __repr__(self):
    #     return '<Item: id=%s>' % self.id

    def __str__(self):
        return u'<{name}: id="{id}" priority={priority} label="{label}">'.format(
                        name=self.__class__.__name__,
                        id=self.id,
                        priority=self._priority,
                        label=self.label,
        )

    def render(self, context, level=0):
        img = self.render_icon(context)
        label = self.render_label(context)

        return format_html(u'<span>{}{}</span>', img, label)

    def render_icon(self, context):
        icon = self.icon

        if icon:
            theme = get_current_theme_from_context(context)

            return get_icon_by_name(icon, theme, label=self.icon_label,
                                    size_px=get_icon_size_px(theme, size='brick-header'),
                                   ).render(css_class='header-menu-icon')

        return ''

    def render_label(self, context):
        return self.label


class ItemList:
    """List of items, ordered with a priority.
    Items must have a '_priority' attribute, reserved to the ItemList it belongs to.
    So an Item cannot be added to several ItemLists (it's checked by the method add()).
    """
    def __init__(self):
        self._items = []
        self._items_ids = set()  # IDs of _items, for fast existence checking.

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def add(self, *items, **kwargs):
        """Adds several Items at once.

        @param items: Instances of Item.
        @param kwargs: A 'priority' (integer) can be specified. All Items will be added with this priority (their
                       original order is kept).
        @return: Self (so you can chain calls).

        If no priority is given, the Items are added at the end.
        """
        ids = self._items_ids

        for item in items:
            if item._priority is not None:
                raise ValueError(u'This item already belongs to a container: {}'.format(item))  # TODO: better exception ?

            if item.id in ids:
                raise ValueError('Duplicated id "{}"'.format(item.id))

        current_items = self._items
        priority = kwargs.pop('priority', None)

        if kwargs:
            raise ValueError('Unknown argument(s): {}'.format(kwargs.keys()))

        if priority is None:
            priority = current_items[-1]._priority if current_items else 1
            current_items.extend(items)
        else:
            for i, in_item in enumerate(reversed(current_items)):
                if in_item._priority <= priority:
                    idx = len(current_items) - i
                    current_items[idx:idx] = items

                    break
            else:
                current_items[0:0] = items

        for item in items:
            item._priority = priority
            ids.add(item.id)

        return self

    def change_priority(self, priority, *item_ids):
        """Changes the priority of N items.
        Helper method, which avoids boilerplate code with pop() + add().

        @param priority: New priority of the Items.
        @param item_ids: IDs of the items.
        """
        pop = self.pop
        self.add(*[pop(item_id) for item_id in item_ids], priority=priority)

    def clear(self):
        """Remove all contented Items"""
        items = self._items
        for item in items:
            item._priority = None

        items[:] = ()
        self._items_ids.clear()

    def get(self, *item_ids):
        """Returns an item by its hierarchy of IDs.

        @param item_ids: Items IDs (strings).
        @return An Item instance (notice that it can be a ContainerItem).
        @raise KeyError.

        Eg: (item_list is an instance of ItemList)
                > item_list.get('management', 'bills')
            It searches the Container with id='management',
            & then searches the Item with id='bills' into this container.
        """
        item_id1 = item_ids[0]
        item_ids = item_ids[1:]

        for item in self._items:
            if item.id == item_id1:
                if not item_ids:
                    return item

                try:
                    get = item.get
                except AttributeError:
                    raise KeyError('"{0}" is not a container.'.format(item_id1))

                return get(*item_ids)

        raise KeyError('"{0}" not found.'.format(item_id1))

    def get_or_create(self, cls, item_id, priority=None, defaults=None):
        """Gets an Item by its ID, or creates it.

        @param cls: The class of the wanted Item.
        @param item_id: The ID of the Item, which is used to find it.
        @param priority: The priority used when the Item is added, if it is created (None means 'at the end').
        @param defaults: Dictionary used as arguments to create the Item if it is not found (notice that
                        'item_id' is automatically used as 'id' argument).
        @return The 'cls' instance.
        @raise ValueError: If the Item exists but has not the given class 'cls'.
        """
        try:
            item = self.get(item_id)
        except KeyError:
            item = cls(id=item_id, **defaults or {})
            self.add(item, priority=priority)
        else:
            if not isinstance(item, cls):
                raise ValueError('The item id="{}" already exists but its type is {}'.format(item_id, item.__class__))

        return item

    def pop(self, item_id):
        """Remove an Item, & return it.

        @param item_id: Item ID.
        @return: The searched Item.
        @raise: KeyError: The Item is not found.
        """
        items = self._items

        for i, item in enumerate(items):
            if item.id == item_id:
                del items[i]
                self._items_ids.remove(item_id)
                item._priority = None
                return item

        raise KeyError('Item with ID={} not found'.format(item_id))

    def remove(self, *item_ids):
        """Remove several Item at once.

        @param item_ids: Item IDs.

        Notice that if some Items are not found, some messages ate logged, but no exception is raised.
        """
        pop = self.pop

        for item_id in item_ids:
            try:
                pop(item_id)
            except KeyError as e:
                logger.warning(e.args[0])


class ItemGroup(Item, ItemList):
    """A container for Items which should be flattened at render (ie: its content is displayed at the same level)"""

    def __init__(self, id, label=''):
        Item.__init__(self, id)
        ItemList.__init__(self)
        self.label = label  # Not a ViewableItem because it's Ok that label & icon are empty

    def __iter__(self):
        label = self.label
        if label:
            yield GroupLabelItem(id=self.id, label=label)

        for item in ItemList.__iter__(self):
            yield item

    def render(self, context, level=0):
        raise ValueError('You should not render an ItemGroup (flatten its content instead)')


class ItemSeparator(Item):
    def __str__(self):
        return '--'

    def render(self, context, level=0):
        return format_html(u'<hr class="ui-creme-navigation-separator ui-creme-navigation-separator-id_{}"/>', self.id)


class ContainerItem(ViewableItem, ItemList):
    """An Item which has child Items.
    The children should be rendered at the deeper level.
    """

    def __init__(self, *args, **kwargs):
        ViewableItem.__init__(self, *args, **kwargs)
        ItemList.__init__(self)

    def __str__(self):
        res = ViewableItem.__str__(self) + '\n'

        for item in self:
            if isinstance(item, ItemGroup):
                res += u'      --Group(id="{}", priority={})\n'.format(item.id, item._priority)

                for sub_item in item:
                    res += u'        {}\n'.format(sub_item)

                res += '      --'
            else:
                res += u'      {}'.format(item)

            res += '\n'

        return res

    def __iter__(self):
        items = list(ItemList.__iter__(self))
        first = True
        last_idx = len(items) - 1
        previous_is_group = False

        for i, item in enumerate(items):
            # TODO: what about nested group (in group) ? forbids or manage ?
            # TODO: attr 'must_be_flattened' ?
            # TODO: avoid separators for empty groups (no title, no item) ?
            if isinstance(item, ItemGroup):
                g_id = item.id

                if not first and not previous_is_group:
                    yield ItemSeparator(id='{}-begin'.format(g_id))

                for sub_item in item:
                    yield sub_item

                if i != last_idx:
                    yield ItemSeparator(id='{}-end'.format(g_id))

                previous_is_group = True
            else:
                yield item
                previous_is_group = False

            first = False

    def render(self, context, level=0):
        level += 1

        return format_html(
            u'{icon}{label}<ul>{li_tags}</ul>',
            icon=self.render_icon(context),
            label=self.render_label(context),
            # TODO: attr 'no_wrapping' instead of isinstance() ??
            li_tags=mark_safe(u''.join(item.render(context, level) if isinstance(item, ItemSeparator) else
                                       format_html(u'<li class="ui-creme-navigation-item-level{level} ui-creme-navigation-item-id_{id}">{item}</li>',
                                                  level=level,
                                                  id=item.id,
                                                  item=item.render(context, level),
                                                )
                                           for item in self
                             )),
        )


class LabelItem(ViewableItem):
    def __init__(self, id,  label, css_classes='ui-creme-navigation-text-entry'):
        super(LabelItem, self).__init__(id=id, label=label)
        self.css_class = css_classes

    def render(self, context, level=0):
        return format_html(u'<span class="{}">{}</span>', self.css_class, self.render_label(context))


class GroupLabelItem(LabelItem):
    "You should not instancing these class (just set a 'label' on your ItemGroup)."
    def __init__(self, id,  label):
        super(GroupLabelItem, self).__init__(id=id, label=label, css_classes='ui-creme-navigation-title')

    def __str__(self):
        return ''


class URLItem(ViewableItem):
    "Item which is rendered as a <a> tag"
    def __init__(self, id, url, *args, **kwargs):
        "@param url: see 'url' property."
        super(URLItem, self).__init__(id, *args, **kwargs)
        self._url = url

    @property
    def url(self):
        "@param url: String or callable returning a string (the string should be a valid URL of course)"
        url = self._url

        return url() if callable(url) else url

    @url.setter
    def url(self, url):
        self._url = url

    @staticmethod
    def list_view(id, model, url=None, label=None, perm=None, **kwargs):
        """Helper method which create an URLItem linking a list-view.

        @param id: ID of the created Item.
        @param model: Model inheriting CremeEntity.
        @param url: URL (see 'url' property). The method 'get_lv_absolute_url' is used as default.
        @param label: Label of the link. The meta.verbose_name_plural is used as default.
        @param perm: permission string (eg: 'persons'). meta.app_label is used as default.
        @param kwargs: Other arguments you want to pass to the constructor.
        @return: The URLItem instance.

        With all these default behaviours, a simple
            > URLItem.list_view('persons-organisations', model=Organisation)
        already gives an acceptable result.
        """
        return URLItem(id=id,
                       url=url or model.get_lv_absolute_url,
                       label=label or model._meta.verbose_name_plural,
                       perm=model._meta.app_label if perm is None else perm,
                       **kwargs
                      )

    @staticmethod
    def creation_view(id, model, url=None, label=None, perm=None, **kwargs):
        """Helper method which create an URLItem linking a creation-view.

        @param id: ID of the created Item.
        @param model: Model inheriting CremeEntity.
        @param url: URL (see 'url' property). The method 'get_create_absolute_url' is used as default.
        @param label: Label of the link. The meta.verbose_name is used as default.
        @param perm: permission string (eg: 'persons.add_contact').
                     Classical creation perm for the given model is used as default
                     (eg: 'persons.add_contact' for Contact).
        @param kwargs: Other arguments you want to pass to the constructor.
        @return: The URLItem instance.

        With all these default behaviours, a simple
            > URLItem.creation_view('persons-create_organisation', model=Organisation)
        already gives an acceptable result.
        """
        return URLItem(id=id,
                       url=url or model.get_create_absolute_url,
                       label=label or model._meta.verbose_name,
                       perm=cperm(model) if perm is None else perm,
                       **kwargs
                      )

    def _has_perm(self, context):
        perm = self.perm

        if perm:
            user = context['user']

            return perm(user) if callable(perm) else user.has_perm(perm)

        return True

    def render(self, context, level=0):
        img = self.render_icon(context)
        label = self.render_label(context)

        if not self._has_perm(context):
            return format_html(u'<span class="ui-creme-navigation-text-entry forbidden">{}{}</span>', img, label)

        return format_html(u'<a href="{url}">{img}{label}</a>', url=self.url, img=img, label=label)


# class OnClickItem(Item):
#     def __init__(self, id, onclick, *args, **kwargs):
#         super(OnClickItem, self).__init__(id, *args, **kwargs)
#         self.onclick = onclick
#
#     def render(self, context):
#         img = self.render_icon(context)
#         label = self.render_label(context)
#
#         perm = self.perm
#         if perm and not context['user'].has_perm(perm):
#             return '<span class="forbidden">%s%s</span>' % (img, label)
#
#         # todo: cache escaped value ??
#         return '<a onclick="%s">%s%s</a>' % (escapejs(self.onclick), img, label)


class TrashItem(URLItem):
    "Item rendering as a link to the Creme trash."
    def __init__(self, id, url=reverse('creme_core__trash')):
        super(TrashItem, self).__init__(id=id, url=url)

    def render(self, context, level=0):
        count = CremeEntity.objects.filter(is_deleted=True).count()

        return format_html(
            u'<a href="{url}">'
                u'{label} <span class="ui-creme-navigation-punctuation">(</span>'
                u'{count}<span class="ui-creme-navigation-punctuation">)</span>'
            u'</a>',
                url=self.url,
                label=_(u'Trash'),
                count=ungettext(u'{count} entity', u'{count} entities', count).format(count=count),
        )

class QuickCreationItemGroup(ItemGroup):  # TODO: 'is_group' + do not inherit ItemGroup ?
    """Item group with a dynamic content, yielded from a QuickFormsRegistry instance."""

    class _QuickCreationItem(ViewableItem):
        def __init__(self, id, ct_id, model, label):
            ViewableItem.__init__(self, id=id, label=label)
            self.ct_id = ct_id
            self.model = model

        def render(self, context, level=0):
            return format_html(u'<a href="#" data-href="{url}" class="quickform-menu-link">{label}</a>',
                               url=reverse('creme_core__quick_forms', args=(self.ct_id, 1)),
                               label=self.label,
                              ) \
                   if context['user'].has_perm_to_create(self.model) else \
                   format_html(u'<span class="ui-creme-navigation-text-entry forbidden">{}</span>', self.label)

    def __init__(self, id, registry, label=ugettext_lazy(u'Quick creation')):
        """@param registry: QuickFormsRegistry instance (indeed, we only need a iter_models() method)."""
        super(QuickCreationItemGroup, self).__init__(id=id, label=label)
        self._registry = registry

    def __iter__(self):
        label = self.label
        if label:
            yield GroupLabelItem(id=self.id, label=label)

        content_types = [(str(model._meta.verbose_name), model) for model in self._registry.iter_models()]
        g_id = self.id

        if content_types:
            get_ct = ContentType.objects.get_for_model
            sort_key = collator.sort_key
            content_types.sort(key=lambda t: sort_key(t[0]))

            for vname, model in content_types:
                ct_id = get_ct(model).id

                yield self._QuickCreationItem(id='{}-{}'.format(g_id, ct_id), ct_id=ct_id, model=model, label=vname)
        else:
            yield LabelItem(id='{}-empty'.format(g_id), label=_(u'No type available'))


class CreationFormsItem(ViewableItem):
    """"Item which displays a specific dialog when you click on it.
    This dialog proposes several creation links, grouped by theme.
    """

    class _Link(Item):
        """Link to a creation view"""
        def __init__(self, id, model=None, **kwargs):
            """Constructor.
            @param id: unique (in this group) string, which allows to do queries (change property, remove...).
            @param model: Class inheriting CremeEntity, or None.
            @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
            If 'model' is None, kwargs arguments are mandatory.
            If 'model' is not None, kwargs arguments override model's information.
            """
            Item.__init__(self, id)
            self.model = model

            if model is not None:
                get = kwargs.get
                self.label = get('label') or model._meta.verbose_name
                # NB: we cannot call model.get_create_absolute_url() immediately because the url resolver
                #     will be used too soon (the apps could be not totally initialized).
                self._url = get('url')
                self.perm = get('perm') or cperm(model)
            else:
                try:
                    self.label = kwargs['label']
                    self._url  = kwargs['url']
                    self.perm  = kwargs['perm']
                except KeyError as e:
                    raise TypeError('Link: missing parameter {}'.format(e))

        def __str__(self):
            return u'<Link: id="{}" label="{}" priority={}>'.format(
                            self.id, self.label, self._priority,
                    )

        @property
        def url(self):
            url = self._url
            model = self.model
            if model:
                if url is None:
                    url = model.get_create_absolute_url()

                    if not url:
                        logger.warning('Beware, the method %s.get_create_absolute_url() should return an URL, '
                                    'or the creation popup will not work correctly' % model
                                   )
                else:
                    url = str(url)
            else:
                url = str(url)

            return url

        def render(self, context, level=0):  # Useless (only to_dict() is used, render is done by JavaScript).
            return format_html(u'<a href="{}">{}</a>', self.url, self.label)

        def to_dict(self, user):
            d = {'label': str(self.label)}

            if user.has_perm(self.perm):  # TODO: accept callable too ?
                d['url'] = self.url

            return d

    class _LinksGroup(ViewableItem):
        """Group of _Link instances."""
        def __init__(self, id, label):
            ViewableItem.__init__(self, id=id, label=label)
            self._links = ItemList()  # We do not inherit to avoid exposing soem ambiguous methods

        def __iter__(self):
            return iter(self._links)

        def __str__(self):
            return u'<LinkGroup: id="{id}" label="{label}" priority={priority}>'.format(
                            id=self.id, label=self.label, priority=self._priority
                    )

        def change_priority(self, priority, *link_ids):
            self._links.change_priority(priority, *link_ids)

        def add_link(self, id, model=None, priority=None, **kwargs):
            """Add a link to a creation view.
            @param id: unique (in this group) string, which allows to do queries (change property, remove...).
            @param priority: Integer indicating priority of the link in this group ('smaller' means 'before').
                             None means the link is added at the (current) end of the group.
            @param model: Class inheriting CremeEntity, or None.
            @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
            If 'model' is None, kwargs arguments are mandatory.
            If 'model' is not None, kwargs arguments override model's information.
            """
            self._links.add(CreationFormsItem._Link(id, model=model, **kwargs), priority=priority)
            return self

        def remove(self, *link_ids):
            self._links.remove(*link_ids)

    def __init__(self, *args, **kwargs):
        super(CreationFormsItem, self).__init__(*args, **kwargs)
        self._groups = ItemList()  # we do not inherit to expose a (slightly) different API

    def as_grid(self, user):
        """ Build JSON-ifiable information  used by JavaScript to render the grid of links.

        @param user: Current user (CremeUser instance).
        @return: list of list of dictionaries.
        """
        # TODO: cache some results ?
        groups = self._groups

        # We compute the size of a square grid which will contain our items
        length = len(groups)
        grid_size = int(math.ceil(math.sqrt(length)))
        holes = grid_size ** 2 - length  # Number of empty cells in the grid

        grid = []
        group_it = iter(groups)

        for row_weigth in range(grid_size, 0, -1):
            row = []

            if not holes:
                col_max_idx = grid_size
            else:
                # We compute the number of holes which remain if we create a hole per (remaining) row
                if holes - row_weigth > 0:
                    holes -= 2
                    col_max_idx = grid_size - 2
                else:
                    holes -= 1
                    col_max_idx = grid_size - 1

            for col_idx in range(col_max_idx):
                link_group = next(group_it)

                row.append({'label': str(link_group.label),
                            'links': [link.to_dict(user) for link in link_group],
                           })

            grid.append(row)

        return grid

    def change_priority(self, priority, *group_ids):
        """"Change the priority of several groups at once.
        See ItemList.change_priority().
        """
        self._groups.change_priority(priority, *group_ids)

    def get_or_create_group(self, group_id, label, priority=None):
        return self._groups.get_or_create(CreationFormsItem._LinksGroup, group_id,
                                          priority=priority, defaults={'label': label},
                                         )

    def remove(self, *group_ids):
        """"Remove several groups at once.
        See ItemList.remove().
        """
        self._groups.remove(*group_ids)

    def render(self, context, level=0):
        return format_html(
            u'<a href="" class="anyform-menu-link" title="{title}" data-grouped-links="{links}">{icon}{label}</a>',
            title=_(u'Create an entity of any type'),
            links=json_dump(self.as_grid(context['user'])),
            icon=self.render_icon(context),
            label=self.render_label(context),
        )

    @property
    def verbose_unicode(self):
        warnings.warn('CreationFormsItem.verbose_unicode() is deprecated ; '
                      'use CreationFormsItem.verbose_str() instead.',
                      DeprecationWarning
                     )
        return self.verbose_str

    @property
    def verbose_str(self):
        """Returns a detailed description of groups/links ; useful to get priorities/IDs."""
        res = u'{}\n'.format(self)

        for group in self._groups:
            res += u'  {}\n'.format(group)

            for link in group:
                res += u'     {}\n'.format(link)

        return res


class LastViewedEntitiesItem(ViewableItem):
    def render(self, context, level=0):
        from .last_viewed import LastViewedItem

        lv_items = LastViewedItem.get_all(context['request'])

        if lv_items:
            li_tags = format_html_join(u'', u'<li><a href="{}">{}</a></li>',
                                       ((lvi.url, lvi.name) for lvi in lv_items)
                                      )
        else:
            li_tags = format_html(u'<li><span class="ui-creme-navigation-text-entry">{}</span></li>',
                                  _(u'No recently visited entity')
                                 )

        return format_html(u'{icon}{label}<ul>{li_tags}</ul>',
                           icon=self.render_icon(context),
                           label=self.render_label(context),
                           li_tags=li_tags,
                          )


class Menu(ItemList):
    # Shortcuts
    LabelItem = LabelItem
    URLItem = URLItem
    ContainerItem = ContainerItem
    ItemGroup = ItemGroup

    def __iter__(self):
        for item in super(Menu, self).__iter__():
            # TODO: what about nested group (in group) ? forbid or manage ?
            # TODO: attr 'must_be_flattened' ?
            if isinstance(item, ItemGroup):
                for sub_item in item:
                    yield sub_item
            else:
                yield item

    def __str__(self):
        # TODO: from cStringIO import StringIO ?
        res = ''

        for item in self:
            if isinstance(item, ItemGroup):
                res += '---\nGroup(id="{}", priority={})\n'.format(item.id, item._priority)

                for sub_item in item:
                    res += u'   {}\n'.format(sub_item)

                res += '---'
            else:
                res += str(item)

            res += '\n'

        return res

    def render(self, context, level=0):
        return format_html(
            u'<ul class="ui-creme-navigation">{}</ul>',
            format_html_join(
                    u'',
                    u'<li class="ui-creme-navigation-item-level{} ui-creme-navigation-item-id_{}">{}</li>',
                    ((level, item.id, item.render(context, level)) for item in self)
            ),
        )

creme_menu = Menu()
