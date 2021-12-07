# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
# import math
from collections import defaultdict
# from typing import Callable, Mapping
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
)

# from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy as reverse
# from django.utils.html import format_html_join
from django.utils.html import format_html, mark_safe
# from django.utils.translation import ngettext
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from ..templatetags.creme_widgets import get_icon_by_name, get_icon_size_px
# from ..utils.media import get_current_theme_from_context
# from ..utils.serializers import json_encode
# from ..utils.unicode_collation import collator
from ..auth import build_creation_perm as cperm
from ..forms import menu as menu_forms
from ..models import CremeEntity, MenuConfigItem

logger = logging.getLogger(__name__)


class MenuEntry:
    """ Base class for entries of of main-menu (displayed on top of all pages).

    The menu has 2 level of entries:
     - level 0 is for root entries (the ones you always see on top)
     - level 1 is for entries related to a level0 entry (their parent), which
       are displayed when you hover the parent.

    Entries can be stored in instances of 'creme_core.model.MenuConfigItem' ;
    but some entries are instances dynamically (see MenuEntrySequence).
    """
    # The ID of an entry class is used to retrieve it from the configuration
    # (see MenuConfigItem.entry_id).
    # Hint: use the classical pattern 'my_app-my_entry'.
    id: str = ''

    # [Optional] Used to generate an extra CSS class (see ContainerEntry) which
    # can be shared by several Entry classes (it's used by Separator1Entry
    # class family).
    # Hint: use the classical pattern 'my_app-my_entry' if you set it.
    type: str = ''

    # The label is a human readable string (generally a gettext_lazy object).
    # The label of the class is used by 'creme_config' to provide its UI.
    # An instance of entry can override the label using the data given by the
    # related instance of MenuConfigItem (see __init__()).
    label: str = ''

    # 0 is for root entries ; level-1 entries correspond to a level-0 entry.
    # It's a class attribute ; instances should not override it.
    level: int = 1  # 0 or 1   # TODO: check ? sub-type ?

    # This attribute is used by 'creme_config': required entry cannot be deleted.
    # It's a class attribute ; instances should not override it.
    is_required = False

    # Classical permissions strings used by the method render(), to avoid
    # redirecting to a forbidden view for example.
    permissions: Union[str, Sequence[str]] = ''

    # These attribute is used by 'creme_config', mainly for special level-1
    # entries which need extra data.
    creation_label = 'Add an entry'
    form_class = menu_forms.MenuEntryForm

    # <True> means that only one instance of entry with the corresponding ID
    # should be created.
    # These attribute is used by 'creme_config', mainly for special level-0
    # entries (if a single-instance entry already exists, it's not proposed anymore).
    single_instance = False

    # <True> means that only the property "children" can be set
    # (currently True only for Container)
    accepts_children = False

    def __init__(self, *,
                 config_item_id: Optional[int] = None,
                 data: Optional[dict] = None,
                 ):
        """ Constructor.
        @param config_item_id: ID of the related instance of MenuConfigItem ;
               it's used by 'creme_config' (notice that it is correctly filled
               by the method 'MenuRegistry.get_entries()'.
        @param data: persistent data which are stored in the related instance
               of MenuConfigItem (see attribute 'entry_data').
        """
        self.config_item_id = config_item_id  # Used by creme_config
        self.data = data = {} if data is None else data  # Used by creme_config
        self.label = data.get('label') or self.label

    def _has_perm(self, context) -> bool:
        permissions = self.permissions

        if permissions:
            user = context['user']
            return (
                user.has_perm(permissions)
                if isinstance(permissions, str) else
                user.has_perms(permissions)
            )

        return True

    @property
    def children(self) -> Iterator['MenuEntry']:
        yield from ()

    def render_label(self, context) -> str:
        return self.label

    def render(self, context) -> str:
        """Render the entry as HTML."""
        return format_html(
            '<span class="ui-creme-navigation-text-entry">{label}</span>',
            label=self.render_label(context),
        )

    @classmethod
    def validate(cls, data: dict) -> dict:
        """Validate the data (passed to the constructor).
        @return: New cleaned dictionary.
        @raise ValidationError.
        """
        # TODO: true user ?
        form = cls.form_class(user=None, data=data)

        for field_name, errors in form.errors.items():
            raise ValidationError(
                errors[0]
                if field_name == '__all__' else
                f'{form.fields[field_name].label} -> {errors[0]}'
            )

        return form.cleaned_data


class MenuEntrySequence(MenuEntry):
    """Represents a sequence of level-1 entries, which are generated dynamically.
    See 'creme_core.menu.QuickFormsEntries' for an example of use.
    """
    def render(self, context):
        raise TypeError('You should not call this method on entry sequence')

    def __iter__(self) -> Iterator[MenuEntry]:
        raise NotImplementedError


class FixedURLEntry(MenuEntry):
    """Base Entry class to display <a> tag with a fixed URL."""
    # URL name of as argument for 'django.urls.reverse()'.
    url_name: str = ''
    label = 'Fixed URL entry'

    form_class = menu_forms.FixedURLEntryForm
    single_instance = True

    @property
    def url(self) -> str:
        url_name = self.url_name
        if url_name:
            return reverse(url_name)

        raise ValueError(f'{self} has an empty URL name.')

    # TODO: factorise
    def render(self, context):
        label = self.render_label(context)

        if not self._has_perm(context):
            return format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{}</span>',
                label,
            )

        return format_html(
            '<a href="{url}">{label}</a>',
            url=self.url,
            label=label,
        )


class CreationEntry(FixedURLEntry):
    """Specialization of FixedURLEntry to redirect to the creation view of an entity class."""
    # Notice that the label, URL & permissions are automatically computed from the model.
    model: Type[CremeEntity] = CremeEntity
    label = 'Creation entry'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model = self.model
        self.label = model.creation_label
        self.permissions = cperm(model)

    @property
    def url(self):
        url = self.model.get_create_absolute_url()

        if not url:
            raise ValueError(
                f'CreationMenuItem: {self.model} has an empty creation URL'
            )

        return url


class ListviewEntry(FixedURLEntry):
    """Specialization of FixedURLEntry to redirect to the list view of an entity class."""
    # Notice that the label, URL & permissions are automatically computed from the model.
    model = CremeEntity
    label = 'Entities'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        meta = self.model._meta
        self.label = meta.verbose_name_plural
        self.permissions = meta.app_label

    @property
    def url(self):
        get_url = getattr(self.model, 'get_lv_absolute_url', None)

        if get_url is None:
            raise ValueError(
                f'ListviewMenuItem: {self.model} has no method "get_lv_absolute_url()"'
            )

        return get_url()


class CustomURLEntry(MenuEntry):
    """Entry display <a> tag with title & URL stored in its data."""
    id = 'creme_core-custom_url'
    label = 'Custom URL entry'

    creation_label = _('Add an URL entry')
    form_class = menu_forms.CustomURLEntryForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = self.data.get('url', '')

    # TODO: factorise ?
    def render(self, context):
        label = self.render_label(context)
        url = self.url

        if not url:
            return format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{}</span>',
                gettext('{label} (broken configuration)').format(label=label),
            )

        return format_html(
            '<a href="{url}">{label}</a>',
            url=url,
            label=label,
        )


class ContainerEntry(MenuEntry):
    """Level-0 Entry which contains level-1 entries.
    Hint: child entries recorded in DataBase use the attribute
          'MenuConfigItem.parent' to reference the instance of 'MenuConfigItem'
          corresponding to the container.
    """
    id = 'creme_core-container'
    level = 0

    # creation_label = ...
    form_class = menu_forms.ContainerEntryForm

    accepts_children = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._children = []

    @property
    def children(self):
        yield from self._children

    @children.setter
    def children(self, children: Iterable[MenuEntry]):
        if self.accepts_children:
            self._children[:] = children
        else:
            logger.warning('%s: children cannot be set', type(self))

    def render(self, context):
        # NB: we flatten entries "contained" by MenuEntrySequences
        def expanded_children():
            for entry in self._children:
                if isinstance(entry, MenuEntrySequence):
                    yield from entry
                else:
                    yield entry

        return format_html(
            '{label}<ul>{li_tags}</ul>',
            label=self.render_label(context),
            li_tags=mark_safe(''.join(
                format_html(
                    '<li class="ui-creme-navigation-item-level1 '
                    '{type_class}'
                    'ui-creme-navigation-item-id_{id}">'
                    '{item}'
                    '</li>',
                    id=entry.id,
                    type_class=(
                        f'ui-creme-navigation-item-type_{entry.type} '
                        if entry.type else ''
                    ),
                    item=entry.render(context),
                )
                for entry in expanded_children()
            )),
        )


class Separator0Entry(MenuEntry):
    """Level-0 separator (currently displayed as a vertical line)."""
    id = 'creme_core-separator0'
    label = _('Separator')
    level = 0

    def render(self, context):
        return ''


class Separator1Entry(MenuEntry):
    """Level-1 separator ; it can have a label stored in DB.
    Currently (ie: theme "icecream" & "chantilly") an horizontal line is
    displayed when it's needed (when the separator is placed between 2
    level-1 entries).
    """
    id = 'creme_core-separator1'
    type = 'creme_core-separator1'
    # label = '----'

    creation_label = _('Add a separator')
    form_class = menu_forms.Separator1EntryForm

    def render(self, context):
        label = self.render_label(context)
        return format_html(
            '<span class="ui-creme-navigation-title">{label}</span>',
            label=label,
        ) if label else ''


class MenuRegistry:
    """Registry for MenuEntry classes which need to be retrieved by their ID
    (because this ID is stored in 'MenuConfigItem.entry_id').
    """
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._entry_classes = {}

    def register(self, *entry_classes: Type[MenuEntry]) -> 'MenuRegistry':
        setdefault = self._entry_classes.setdefault

        for entry_cls in entry_classes:
            entry_id = entry_cls.id

            if not entry_id:
                raise self.RegistrationError(f"Entry class with empty id_: {entry_cls}")

            if '"' in entry_id or "'" in entry_id:
                raise self.RegistrationError(
                    f"""Entry ID cannot contain <"'> characters: {entry_id}"""
                )

            if setdefault(entry_id, entry_cls) is not entry_cls:
                raise self.RegistrationError(f"Duplicated entry's id: {entry_id}")

        return self

    def get_class(self, entry_id: str) -> Optional[Type[MenuEntry]]:
        return self._entry_classes.get(entry_id)

    @property
    def entry_classes(self) -> Iterator[Type[MenuEntry]]:
        yield from self._entry_classes.values()

    def get_entries(self, config_items: Iterable[MenuConfigItem]) -> List[MenuEntry]:
        """Get instances corresponding some MenuConfigItems.
        Parenting is managed ; and attributes 'config_item_id' are filled.
        """
        # TODO: generalise with deeper levels ?
        entry_info = [[], []]  # NB: 2 lists for 2 levels
        get_class = self._entry_classes.get

        for item in config_items:
            cls = get_class(item.entry_id)
            if cls is None:
                logger.warning(
                    'MenuRegistry.get_entries(): invalid entry class with id="%s"',
                    item.entry_id,
                )
            else:
                try:
                    entry_info[cls.level].append((cls, item))
                except IndexError:
                    logger.warning(
                        'MenuRegistry.get_entries(): invalid level %s in class %s',
                        cls.level, cls,
                    )

        children = defaultdict(list)
        for entry_cls, item in entry_info[1]:
            children[item.parent_id].append(
                entry_cls(config_item_id=item.id, data=item.entry_data)
            )

        entries = []
        for entry_cls, item in entry_info[0]:
            entry = entry_cls(config_item_id=item.id, data=item.entry_data)
            if entry.accepts_children:
                entry.children = children[item.id]

            entries.append(entry)

        return entries


menu_registry = MenuRegistry().register(
    ContainerEntry,
    Separator0Entry,
    Separator1Entry,
    CustomURLEntry,
)

# Other creation entry ---------------------------------------------------------


class _PriorityList:
    """List of object with an "id", ordered with a priority.
    (internal to CreationViewsRegistry)
    Items must have a '_priority' attribute, reserved to the _PriorityList it belongs to.
    """

    def __init__(self):
        self._items = []
        self._ids: Set[str] = set()  # IDs of _items, for fast existence checking.

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def add(self, *items, **kwargs) -> '_PriorityList':
        """Adds several items at once.

        @param items: Instances.
        @param kwargs: A 'priority' (integer) can be specified. All Items will
               be added with this priority (their original order is kept).
        @return: Self (so you can chain calls).

        If no priority is given, the Items are added at the end.
        """
        ids = self._ids

        for item in items:
            if item._priority is not None:
                raise ValueError(
                    f'This item already belongs to a container: {item}'
                )  # TODO: better exception ?

            if item.id in ids:
                raise ValueError(f'Duplicated id "{item.id}"')

        current_items = self._items
        priority = kwargs.pop('priority', None)

        if kwargs:
            raise ValueError(f'Unknown argument(s): {kwargs.keys()}')

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

    def change_priority(self, priority: int, *item_ids: str) -> None:
        """Changes the priority of N items.
        Helper method, which avoids boilerplate code with pop() + add().

        @param priority: New priority of the Items.
        @param item_ids: IDs of the items.
        """
        pop = self.pop
        self.add(*[pop(item_id) for item_id in item_ids], priority=priority)

    # TODO ??
    # def clear(self) -> None:
    #     """Remove all contained Items"""
    #     items = self._items
    #     for item in items:
    #         item._priority = None
    #
    #     items.clear()
    #     self._items_ids.clear()

    def get(self, item_id):
        for item in self._items:
            if item.id == item_id:
                return item

        raise KeyError(f'"{item_id}" not found.')

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
                self._ids.remove(item_id)
                item._priority = None
                return item

        raise KeyError(f'Item with ID={item_id} not found')

    def remove(self, *item_ids) -> None:
        """Remove several Item at once.

        @param item_ids: item IDs.

        Notice that if some Items are not found, some messages ate logged,
        but no exception is raised.
        """
        pop = self.pop

        for item_id in item_ids:
            try:
                pop(item_id)
            except KeyError as e:
                logger.warning(e.args[0])

        # return self  TODO ?


class _CreationViewLink:
    def __init__(self, id, model: Optional[Type[CremeEntity]] = None, **kwargs):
        """Constructor.
        @param id: unique (in this group) string, which allows to do queries
               (change property, remove...).
        @param model: Class inheriting CremeEntity, or None.
        @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
        If 'model' is None, kwargs arguments are mandatory.
        If 'model' is not None, kwargs arguments override model's information.
        """
        self.id = id
        self.model = model
        self._priority = None

        if model is not None:
            get = kwargs.get
            self.label = get('label') or model._meta.verbose_name
            # NB: we cannot call model.get_create_absolute_url() immediately
            #     because the url resolver will be used too soon
            #     (the apps could be not totally initialized).
            self._url = get('url')
            self.perm = get('perm') or cperm(model)
        else:
            try:
                self.label = kwargs['label']
                self._url = kwargs['url']
                self.perm = kwargs['perm']
            except KeyError as e:
                raise TypeError(f'_Link: missing parameter {e}') from e

    def __str__(self):
        return f'<Link: id="{self.id}" label="{self.label}" priority={self._priority}>'

    @property
    def url(self) -> str:
        url = self._url
        model = self.model
        if model:
            if url is None:
                url = model.get_create_absolute_url()

                if not url:
                    logger.warning(
                        'Beware, the method %s.get_create_absolute_url() should '
                        'return an URL, or the creation popup will not work correctly',
                        model,
                    )
            else:
                url = str(url)
        else:
            url = str(url)

        return url

    def to_dict(self, user) -> Dict[str, str]:
        d = {'label': str(self.label)}

        if user.has_perm(self.perm):  # TODO: accept callable too ?
            d['url'] = self.url

        return d


class _CreationViewLinksGroup:
    """Group of _CreationViewLink instances."""
    link_class = _CreationViewLink

    def __init__(self, id, label):
        self.id = id
        self.label = label
        # We do not inherit to avoid exposing some ambiguous methods
        self._links = _PriorityList()
        self._priority = None

    def __iter__(self):
        return iter(self._links)

    def __str__(self):
        return f'<Group: id="{self.id}" label="{self.label}" priority={self._priority}>'

    def change_links_priority(self, priority, *link_ids):
        self._links.change_priority(priority, *link_ids)

    def add_link(
            self,
            id: str,
            model=None,
            priority=None,
            **kwargs) -> '_CreationViewLinksGroup':
        """Add a link to a creation view.
        @param id: unique (in this group) string, which allows to do queries
               (change property, remove...).
        @param priority: Integer indicating priority of the link in this group
               ('smaller' means 'before').
               <None> means the link is added at the (current) end of the group.
        @param model: Class inheriting CremeEntity, or None.
        @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
        If 'model' is None, kwargs arguments are mandatory.
        If 'model' is not None, kwargs arguments override model's information.
        """
        self._links.add(
            self.link_class(id, model=model, **kwargs),
            priority=priority,
        )
        return self

    def remove_links(self, *link_ids: str) -> None:
        self._links.remove(*link_ids)


class CreationMenuRegistry:
    def __init__(self, group_class=_CreationViewLinksGroup):
        self._group_class = group_class
        # NB: we do not inherit to expose a (slightly) different API
        self._groups = _PriorityList()

    def __iter__(self):
        return iter(self._groups)

    def change_groups_priority(self, priority, *group_ids):
        """"Change the priority of several groups at once.
        See _PriorityList.change_priority().
        """
        self._groups.change_priority(priority, *group_ids)

    def get_or_create_group(
            self,
            group_id: str,
            label,
            priority=None) -> '_CreationViewLinksGroup':
        """Get a group of links by its ID, & create it if it does not exist."""
        groups = self._groups

        try:
            group = groups.get(group_id)
        except KeyError:
            group = self._group_class(id=group_id, label=label)
            groups.add(group, priority=priority)

        return group

    def remove_groups(self, *group_ids: str) -> None:
        """"Remove several groups at once.
        See _PriorityList.remove().
        """
        self._groups.remove(*group_ids)

    @property
    def verbose_str(self) -> str:
        """Returns a detailed description of groups/links ; useful to get priorities/IDs."""
        res = f'{type(self).__name__}:\n'

        for group in self._groups:
            res += f'  {group}\n'

            for link in group:
                res += f'    {link}\n'

        return res


creation_menu_registry = CreationMenuRegistry()

# ------------------------------------------------------------------------------


# def _validate_id(id_: str) -> str:
#     if '"' in id_ or "'" in id_:
#         raise ValueError("""ID cannot contain <"'> characters.""")
#
#     return id_


# class Item:
#     def __init__(self, id: str):
#         self.id: str = _validate_id(id)
#         self._priority: Optional[int] = None
#
#     @property
#     def priority(self) -> Optional[int]:
#         "Priority inside its container (see ItemList)."
#         return self._priority
#
#     def render(self, context, level: int = 0) -> str:
#         """Render as HTML.
#
#         @param context: Context of the Template where the Item is rendered (dictionary).
#                         We probably need theme name etc...
#         @param level: Integer indicating the level of depth in the menu ;
#                0 is first, 1 is second.
#         @return: HTML string.
#         """
#         raise NotImplementedError


# class ViewableItem(Item):
#     def __init__(self,
#                  id: str,
#                  label: str = '',
#                  icon: Optional[str] = None,
#                  icon_label: str = '',
#                  perm=None):
#         """
#         @param id: Identifier (string). Must be unique in a container.
#                A good way is to prefix with app label + '-'.
#         @param label: Text displayed for this entry
#                (should be a gettext_lazy or something like that).
#         @param icon: Icon identifier (string -- see icon system).
#                Size used is 'brick-header'.
#         @param icon_label: Label of the related icon (not used if 'icon' is None).
#         @param perm: Permission (a not allowed entry will be disabled) ;
#                can be a classical permission string (eg: 'persons', 'persons.add_contact')
#                or a callable which takes one argument (user) & returns a boolean.
#         """
#         super().__init__(id)
#         # TODO: assert there is at least an icon or a label ????
#         self.label = label
#         self.icon = icon
#         self.icon_label = icon_label or label
#         self.perm = perm
#
#     def __str__(self):
#         return (
#             f'<{self.__class__.__name__}: '
#             f'id="{self.id}" priority={self._priority} label="{self.label}"'
#             f'>'
#         )
#
#     def render(self, context, level=0):
#         img = self.render_icon(context)
#         label = self.render_label(context)
#
#         return format_html('<span>{}{}</span>', img, label)
#
#     def render_icon(self, context) -> str:
#         icon = self.icon
#
#         if icon:
#             theme = get_current_theme_from_context(context)
#
#             return get_icon_by_name(icon, theme, label=self.icon_label,
#                                     size_px=get_icon_size_px(theme, size='brick-header'),
#                                    ).render(css_class='header-menu-icon')
#
#         return ''
#
#     def render_label(self, context):
#         return self.label


# class ItemList:
#     """List of items, ordered with a priority.
#     Items must have a '_priority' attribute, reserved to the ItemList it belongs to.
#     So an Item cannot be added to several ItemLists (it's checked by the method add()).
#     """
#     def __init__(self):
#         self._items: List[Item] = []
#         self._items_ids: Set[str] = set()  # IDs of _items, for fast existence checking.
#
#     def __iter__(self) -> Iterator[Item]:
#         return iter(self._items)
#
#     def __len__(self):
#         return len(self._items)
#
#     def add(self, *items: Item, **kwargs) -> 'ItemList':
#         """Adds several Items at once.
#
#         @param items: Instances of Item.
#         @param kwargs: A 'priority' (integer) can be specified. All Items will
#                be added with this priority (their original order is kept).
#         @return: Self (so you can chain calls).
#
#         If no priority is given, the Items are added at the end.
#         """
#         ids = self._items_ids
#
#         for item in items:
#             if item._priority is not None:
#                 raise ValueError(
#                     f'This item already belongs to a container: {item}'
#                 )
#
#             if item.id in ids:
#                 raise ValueError(f'Duplicated id "{item.id}"')
#
#         current_items = self._items
#         priority = kwargs.pop('priority', None)
#
#         if kwargs:
#             raise ValueError(f'Unknown argument(s): {kwargs.keys()}')
#
#         if priority is None:
#             priority = current_items[-1]._priority if current_items else 1
#             current_items.extend(items)
#         else:
#             for i, in_item in enumerate(reversed(current_items)):
#                 if in_item._priority <= priority:
#                     idx = len(current_items) - i
#                     current_items[idx:idx] = items
#
#                     break
#             else:
#                 current_items[0:0] = items
#
#         for item in items:
#             item._priority = priority
#             ids.add(item.id)
#
#         return self
#
#     def change_priority(self, priority: int, *item_ids: str) -> None:
#         """Changes the priority of N items.
#         Helper method, which avoids boilerplate code with pop() + add().
#
#         @param priority: New priority of the Items.
#         @param item_ids: IDs of the items.
#         """
#         pop = self.pop
#         self.add(*[pop(item_id) for item_id in item_ids], priority=priority)
#
#     def clear(self) -> None:
#         """Remove all contented Items"""
#         items = self._items
#         for item in items:
#             item._priority = None
#
#         items.clear()
#         self._items_ids.clear()
#
#     def get(self, *item_ids: str) -> Item:
#         """Returns an item by its hierarchy of IDs.
#
#         @param item_ids: Items IDs (strings).
#         @return An Item instance (notice that it can be a ContainerItem).
#         @raise KeyError.
#
#         Eg: (item_list is an instance of ItemList)
#                 > item_list.get('management', 'bills')
#             It searches the Container with id='management',
#             & then searches the Item with id='bills' into this container.
#         """
#         item_id1 = item_ids[0]
#         item_ids = item_ids[1:]
#
#         for item in self._items:
#             if item.id == item_id1:
#                 if not item_ids:
#                     return item
#
#                 try:
#                     get = item.get
#                 except AttributeError as e:
#                     raise KeyError(f'"{item_id1}" is not a container.') from e
#
#                 return get(*item_ids)
#
#         raise KeyError(f'"{item_id1}" not found.')
#
#     def get_or_create(self,
#                       cls: Type[Item],
#                       item_id: str,
#                       priority: Optional[int] = None,
#                       defaults: Optional[Mapping] = None):
#         """Gets an Item by its ID, or creates it.
#
#         @param cls: The class of the wanted Item.
#         @param item_id: The ID of the Item, which is used to find it.
#         @param priority: The priority used when the Item is added,
#                if it is created (None means 'at the end').
#         @param defaults: Dictionary used as arguments to create the Item if it
#                is not found (notice that 'item_id' is automatically used as 'id' argument).
#         @return The 'cls' instance.
#         @raise ValueError: If the Item exists but has not the given class 'cls'.
#         """
#         try:
#             item = self.get(item_id)
#         except KeyError:
#             item = cls(id=item_id, **defaults or {})
#             self.add(item, priority=priority)
#         else:
#             if not isinstance(item, cls):
#                 raise ValueError(
#                     f'The item id="{item_id}" already exists but its type is {item.__class__}'
#                 )
#
#         return item
#
#     def pop(self, item_id: str) -> Item:
#         """Remove an Item, & return it.
#
#         @param item_id: Item ID.
#         @return: The searched Item.
#         @raise: KeyError: The Item is not found.
#         """
#         items = self._items
#
#         for i, item in enumerate(items):
#             if item.id == item_id:
#                 del items[i]
#                 self._items_ids.remove(item_id)
#                 item._priority = None
#                 return item
#
#         raise KeyError(f'Item with ID={item_id} not found')
#
#     def remove(self, *item_ids: str) -> None:
#         """Remove several Item at once.
#
#         @param item_ids: Item IDs.
#
#         Notice that if some Items are not found, some messages ate logged,
#         but no exception is raised.
#         """
#         pop = self.pop
#
#         for item_id in item_ids:
#             try:
#                 pop(item_id)
#             except KeyError as e:
#                 logger.warning(e.args[0])


# class ItemGroup(Item, ItemList):
#     """A container for Items which should be flattened at render
#     (ie: its content is displayed at the same level).
#     """
#
#     def __init__(self, id, label=''):
#         Item.__init__(self, id)
#         ItemList.__init__(self)
#         self.label = label  # Not a ViewableItem because it's Ok that label & icon are empty
#
#     def __iter__(self) -> Iterator[Item]:
#         label = self.label
#         if label:
#             yield GroupLabelItem(id=self.id, label=label)
#
#         for item in ItemList.__iter__(self):
#             yield item
#
#     def render(self, context, level=0) -> str:
#         raise ValueError('You should not render an ItemGroup (flatten its content instead)')


# class ItemSeparator(Item):
#     def __str__(self):
#         return '--'
#
#     def render(self, context, level=0):
#         return format_html(
#             '<hr class="ui-creme-navigation-separator ui-creme-navigation-separator-id_{}"/>',
#             self.id,
#         )


# class ContainerItem(ViewableItem, ItemList):
#     """An Item which has child Items.
#     The children should be rendered at the deeper level.
#     """
#
#     def __init__(self, *args, **kwargs):
#         ViewableItem.__init__(self, *args, **kwargs)
#         ItemList.__init__(self)
#
#     def __str__(self):
#         res = ViewableItem.__str__(self) + '\n'
#
#         for item in self:
#             if isinstance(item, ItemGroup):
#                 res += f'      --Group(id="{item.id}", priority={item._priority})\n'
#
#                 for sub_item in item:
#                     res += f'        {sub_item}\n'
#
#                 res += '      --'
#             else:
#                 res += f'      {item}'
#
#             res += '\n'
#
#         return res
#
#     def __iter__(self):
#         items = [*ItemList.__iter__(self)]
#         first = True
#         last_idx = len(items) - 1
#         previous_is_group = False
#
#         for i, item in enumerate(items):
#             if isinstance(item, ItemGroup):
#                 g_id = item.id
#
#                 if not first and not previous_is_group:
#                     yield ItemSeparator(id=f'{g_id}-begin')
#
#                 for sub_item in item:
#                     yield sub_item
#
#                 if i != last_idx:
#                     yield ItemSeparator(id=f'{g_id}-end')
#
#                 previous_is_group = True
#             else:
#                 yield item
#                 previous_is_group = False
#
#             first = False
#
#     def render(self, context, level=0):
#         level += 1
#
#         return format_html(
#             '{icon}{label}<ul>{li_tags}</ul>',
#             icon=self.render_icon(context),
#             label=self.render_label(context),
#             li_tags=mark_safe(
#                 ''.join(
#                     item.render(context, level)
#                     if isinstance(item, ItemSeparator) else
#                     format_html(
#                         '<li class="ui-creme-navigation-item-level{level} '
#                         'ui-creme-navigation-item-id_{id}">'
#                         '{item}'
#                         '</li>',
#                         level=level,
#                         id=item.id,
#                         item=item.render(context, level),
#                     )
#                     for item in self
#                 )
#             ),
#         )


# class LabelItem(ViewableItem):
#     def __init__(self, id,  label, css_classes='ui-creme-navigation-text-entry'):
#         super().__init__(id=id, label=label)
#         self.css_class = css_classes
#
#     def render(self, context, level=0):
#         return format_html(
#             '<span class="{}">{}</span>',
#             self.css_class,
#             self.render_label(context),
#         )


# class GroupLabelItem(LabelItem):
#     "You should not instancing this class (just set a 'label' on your ItemGroup)."
#     def __init__(self, id,  label):
#         super().__init__(id=id, label=label, css_classes='ui-creme-navigation-title')
#
#     def __str__(self):
#         return ''


# _URL = Union[Callable[[], str], str]


# class URLItem(ViewableItem):
#     "Item which is rendered as a <a> tag."
#     def __init__(self, id, url: _URL, *args, **kwargs):
#         "@param url: see 'url' property."
#         super().__init__(id, *args, **kwargs)
#         self._url = url
#
#     @property
#     def url(self) -> str:
#         url = self._url
#
#         return url() if callable(url) else url
#
#     @url.setter
#     def url(self, url: _URL):
#         """@param url: String or callable returning a string
#                   (the string should be a valid URL of course).
#         """
#         self._url = url
#
#     @classmethod
#     def list_view(cls,
#                   id: str,
#                   model: Type[CremeEntity],
#                   url: Optional[_URL] = None,
#                   label: Optional[str] = None,
#                   perm: Optional[str] = None,
#                   **kwargs) -> 'URLItem':
#         """Helper method which create an URLItem linking a list-view.
#
#         @param id: ID of the created Item.
#         @param model: Model inheriting CremeEntity.
#         @param url: URL (see 'url' property). The method 'get_lv_absolute_url'
#                is used as default.
#         @param label: Label of the link. The meta.verbose_name_plural is used as default.
#         @param perm: permission string (eg: 'persons'). meta.app_label is used as default.
#         @param kwargs: Other arguments you want to pass to the constructor.
#         @return: The URLItem instance.
#
#         With all these default behaviours, a simple
#             > URLItem.list_view('persons-organisations', model=Organisation)
#         already gives an acceptable result.
#         """
#         if url is None:
#             url = getattr(model, 'get_lv_absolute_url', None)
#
#             if url is None:
#                 raise ValueError(
#                     'URLItem.list_view(): '
#                     'pass an URL or add a method get_lv_absolute_url() in the model.'
#                 )
#
#         return cls(
#             id=id,
#             url=url,
#             label=label or model._meta.verbose_name_plural,
#             perm=model._meta.app_label if perm is None else perm,
#             **kwargs
#         )
#
#     @classmethod
#     def creation_view(cls,
#                       id: str,
#                       model: Type[CremeEntity],
#                       url: Optional[_URL] = None,
#                       label: Optional[str] = None,
#                       perm: Optional[str] = None,
#                       **kwargs) -> 'URLItem':
#         """Helper method which create an URLItem linking a creation-view.
#
#         @param id: ID of the created Item.
#         @param model: Model inheriting CremeEntity.
#         @param url: URL (see 'url' property).
#                     The method 'get_create_absolute_url' is used as default.
#         @param label: Label of the link. The meta.verbose_name is used as default.
#         @param perm: permission string (eg: 'persons.add_contact').
#                      Classical creation perm for the given model is used as default
#                      (eg: 'persons.add_contact' for Contact).
#         @param kwargs: Other arguments you want to pass to the constructor.
#         @return: The URLItem instance.
#
#         With all these default behaviours, a simple
#             > URLItem.creation_view('persons-create_organisation', model=Organisation)
#         already gives an acceptable result.
#         """
#         return cls(
#             id=id,
#             url=url or model.get_create_absolute_url,
#             label=label or model._meta.verbose_name,
#             perm=cperm(model) if perm is None else perm,
#             **kwargs
#         )
#
#     def _has_perm(self, context) -> bool:
#         perm = self.perm
#
#         if perm:
#             user = context['user']
#
#             return perm(user) if callable(perm) else user.has_perm(perm)
#
#         return True
#
#     def render(self, context, level=0):
#         img = self.render_icon(context)
#         label = self.render_label(context)
#
#         if not self._has_perm(context):
#             return format_html(
#                 '<span class="ui-creme-navigation-text-entry forbidden">{}{}</span>',
#                 img, label,
#             )
#
#         return format_html(
#             '<a href="{url}">{img}{label}</a>',
#             url=self.url,
#             img=img,
#             label=label,
#         )


# class TrashItem(URLItem):
#     "Item rendering as a link to the Creme trash."
#     def __init__(self, id, url=reverse('creme_core__trash')):
#         super().__init__(id=id, url=url)
#
#     def render(self, context, level=0):
#         count = CremeEntity.objects.filter(is_deleted=True).count()
#
#         return format_html(
#             '<a href="{url}">'
#             '{label} '
#             '<span class="ui-creme-navigation-punctuation">(</span>'
#             '{count}'
#             '<span class="ui-creme-navigation-punctuation">)</span>'
#             '</a>',
#             url=self.url,
#             label=_('Trash'),
#             count=ngettext(
#                 '{count} entity',
#                 '{count} entities',
#                 count,
#             ).format(count=count),
#         )


# class QuickCreationItemGroup(ItemGroup):
#     """Item group with a dynamic content, yielded from a QuickFormsRegistry instance."""
#
#     class _QuickCreationItem(ViewableItem):
#         def __init__(self, id, ct_id: int, model: Type[CremeEntity], label):
#             ViewableItem.__init__(self, id=id, label=label)
#             self.ct_id = ct_id
#             self.model = model
#
#         def render(self, context, level=0):
#             return format_html(
#                 '<a href="#" data-href="{url}" class="quickform-menu-link">{label}</a>',
#                 url=reverse('creme_core__quick_form', args=(self.ct_id,)),
#                 label=self.label,
#             ) if context['user'].has_perm_to_create(self.model) else format_html(
#                 '<span class="ui-creme-navigation-text-entry forbidden">{}</span>',
#                 self.label,
#             )
#
#     def __init__(self, id: str, registry, label=gettext_lazy('Quick creation')):
#         """Constructor.
#         @param registry: QuickFormsRegistry instance
#                (indeed, we only need a iter_models() method).
#         """
#         super().__init__(id=id, label=label)
#         self._registry = registry
#
#     def __iter__(self):
#         label = self.label
#         if label:
#             yield GroupLabelItem(id=self.id, label=label)
#
#         content_types = [
#             (str(model._meta.verbose_name), model)
#             for model in self._registry.models
#         ]
#         g_id = self.id
#
#         if content_types:
#             get_ct = ContentType.objects.get_for_model
#             sort_key = collator.sort_key
#             content_types.sort(key=lambda t: sort_key(t[0]))
#
#             for vname, model in content_types:
#                 ct_id = get_ct(model).id
#
#                 yield self._QuickCreationItem(
#                     id=f'{g_id}-{ct_id}', ct_id=ct_id, model=model, label=vname,
#                 )
#         else:
#             yield LabelItem(id=f'{g_id}-empty', label=_('No type available'))


# class CreationFormsItem(ViewableItem):
#     """"Item which displays a specific dialog when you click on it.
#     This dialog proposes several creation links, grouped by theme.
#     """
#
#     class _Link(Item):
#         """Link to a creation view."""
#         def __init__(self, id, model: Optional[Type[CremeEntity]] = None, **kwargs):
#             """Constructor.
#             @param id: unique (in this group) string, which allows to do queries
#                    (change property, remove...).
#             @param model: Class inheriting CremeEntity, or None.
#             @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
#             If 'model' is None, kwargs arguments are mandatory.
#             If 'model' is not None, kwargs arguments override model's information.
#             """
#             Item.__init__(self, id)
#             self.model = model
#
#             if model is not None:
#                 get = kwargs.get
#                 self.label = get('label') or model._meta.verbose_name
#                 # NB: we cannot call model.get_create_absolute_url() immediately
#                 #     because the url resolver will be used too soon
#                 #     (the apps could be not totally initialized).
#                 self._url = get('url')
#                 self.perm = get('perm') or cperm(model)
#             else:
#                 try:
#                     self.label = kwargs['label']
#                     self._url  = kwargs['url']
#                     self.perm  = kwargs['perm']
#                 except KeyError as e:
#                     raise TypeError(f'Link: missing parameter {e}') from e
#
#         def __str__(self):
#             return f'<Link: id="{self.id}" label="{self.label}" priority={self._priority}>'
#
#         @property
#         def url(self) -> str:
#             url = self._url
#             model = self.model
#             if model:
#                 if url is None:
#                     url = model.get_create_absolute_url()
#
#                     if not url:
#                         logger.warning(
#                             'Beware, the method %s.get_create_absolute_url() should '
#                             'return an URL, or the creation popup will not work correctly',
#                             model,
#                         )
#                 else:
#                     url = str(url)
#             else:
#                 url = str(url)
#
#             return url
#
#         # Useless (only to_dict() is used, render is done by JavaScript).
#         def render(self, context, level=0):
#             return format_html('<a href="{}">{}</a>', self.url, self.label)
#
#         def to_dict(self, user) -> Dict[str, str]:
#             d = {'label': str(self.label)}
#
#             if user.has_perm(self.perm):
#                 d['url'] = self.url
#
#             return d
#
#     class _LinksGroup(ViewableItem):
#         """Group of _Link instances."""
#         def __init__(self, id, label):
#             ViewableItem.__init__(self, id=id, label=label)
#             # We do not inherit to avoid exposing some ambiguous methods
#             self._links = ItemList()
#
#         def __iter__(self):
#             return iter(self._links)
#
#         def __str__(self):
#             return f'<LinkGroup: id="{self.id}" label="{self.label}" priority={self._priority}>'
#
#         def change_priority(self, priority, *link_ids):
#             self._links.change_priority(priority, *link_ids)
#
#         def add_link(
#                 self,
#                 id: str,
#                 model=None,
#                 priority=None,
#                 **kwargs) -> 'CreationFormsItem._LinksGroup':
#             """Add a link to a creation view.
#             @param id: unique (in this group) string, which allows to do queries
#                    (change property, remove...).
#             @param priority: Integer indicating priority of the link in this group
#                    ('smaller' means 'before').
#                    <None> means the link is added at the (current) end of the group.
#             @param model: Class inheriting CremeEntity, or None.
#             @param kwargs: Optional arguments: 'label', 'url' & 'perm' (strings).
#             If 'model' is None, kwargs arguments are mandatory.
#             If 'model' is not None, kwargs arguments override model's information.
#             """
#             self._links.add(
#                 CreationFormsItem._Link(id, model=model, **kwargs), priority=priority
#             )
#             return self
#
#         def remove(self, *link_ids: str) -> None:
#             self._links.remove(*link_ids)
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._groups = ItemList()  # we do not inherit to expose a (slightly) different API
#
#     def as_grid(self, user) -> List[List[dict]]:
#         """ Build JSON-ifiable information  used by JavaScript to render the grid of links.
#
#         @param user: Current user (CremeUser instance).
#         @return: list of list of dictionaries.
#         """
#         groups = self._groups
#
#         # We compute the size of a square grid which will contain our items
#         length = len(groups)
#         grid_size = int(math.ceil(math.sqrt(length)))
#         holes = grid_size ** 2 - length  # Number of empty cells in the grid
#
#         grid = []
#         group_it = iter(groups)
#
#         for row_weigth in range(grid_size, 0, -1):
#             row = []
#
#             if not holes:
#                 col_max_idx = grid_size
#             else:
#                 # We compute the number of holes which remain if we create a
#                 # hole per (remaining) row
#                 if holes - row_weigth > 0:
#                     holes -= 2
#                     col_max_idx = grid_size - 2
#                 else:
#                     holes -= 1
#                     col_max_idx = grid_size - 1
#
#             for col_idx in range(col_max_idx):
#                 link_group = next(group_it)
#
#                 row.append({'label': str(link_group.label),
#                             'links': [link.to_dict(user) for link in link_group],
#                            })
#
#             grid.append(row)
#
#         return grid
#
#     def change_priority(self, priority, *group_ids):
#         """"Change the priority of several groups at once.
#         See ItemList.change_priority().
#         """
#         self._groups.change_priority(priority, *group_ids)
#
#     def get_or_create_group(
#             self,
#             group_id: str,
#             label,
#             priority=None) -> 'CreationFormsItem._LinksGroup':
#         return self._groups.get_or_create(CreationFormsItem._LinksGroup, group_id,
#                                           priority=priority, defaults={'label': label},
#                                          )
#
#     def remove(self, *group_ids: str) -> None:
#         """"Remove several groups at once.
#         See ItemList.remove().
#         """
#         self._groups.remove(*group_ids)
#
#     def render(self, context, level=0):
#         return format_html(
#             '<a href="" class="anyform-menu-link" title="{title}" data-grouped-links="{links}">'
#             '{icon}{label}'
#             '</a>',
#             title=_('Create an entity of any type'),
#             links=json_encode(self.as_grid(context['user'])),
#             icon=self.render_icon(context),
#             label=self.render_label(context),
#         )
#
#     @property
#     def verbose_str(self) -> str:
#         """Returns a detailed description of groups/links ; useful to get priorities/IDs."""
#         res = f'{self}\n'
#
#         for group in self._groups:
#             res += f'  {group}\n'
#
#             for link in group:
#                 res += f'     {link}\n'
#
#         return res


# class LastViewedEntitiesItem(ViewableItem):
#     def render(self, context, level=0):
#         from .last_viewed import LastViewedItem
#
#         lv_items = LastViewedItem.get_all(context['request'])
#
#         if lv_items:
#             li_tags = format_html_join('', '<li><a href="{}">{}</a></li>',
#                                        ((lvi.url, lvi.name) for lvi in lv_items)
#                                       )
#         else:
#             li_tags = format_html(
#                 '<li><span class="ui-creme-navigation-text-entry">{}</span></li>',
#                 _('No recently visited entity')
#             )
#
#         return format_html('{icon}{label}<ul>{li_tags}</ul>',
#                            icon=self.render_icon(context),
#                            label=self.render_label(context),
#                            li_tags=li_tags,
#                           )


# class Menu(ItemList):
#     # Shortcuts
#     LabelItem = LabelItem
#     URLItem = URLItem
#     ContainerItem = ContainerItem
#     ItemGroup = ItemGroup
#
#     def __iter__(self):
#         for item in super().__iter__():
#             if isinstance(item, ItemGroup):
#                 for sub_item in item:
#                     yield sub_item
#             else:
#                 yield item
#
#     def __str__(self):
#         res = ''
#
#         for item in self:
#             if isinstance(item, ItemGroup):
#                 res += f'---\nGroup(id="{item.id}", priority={item._priority})\n'
#
#                 for sub_item in item:
#                     res += f'   {sub_item}\n'
#
#                 res += '---'
#             else:
#                 res += str(item)
#
#             res += '\n'
#
#         return res
#
#     def render(self, context, level=0):
#         return format_html(
#             '<ul class="ui-creme-navigation">{}</ul>',
#             format_html_join(
#                 '',
#                 '<li class="ui-creme-navigation-item-level{} ui-creme-navigation-item-id_{}">'
#                 '{}'
#                 '</li>',
#                 ((level, item.id, item.render(context, level)) for item in self)
#             ),
#         )


# creme_menu = Menu()
