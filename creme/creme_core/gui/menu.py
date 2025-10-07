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

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy as reverse
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .. import auth
from ..forms import menu as menu_forms
from ..models import CremeEntity, CremeUser, CustomEntityType, MenuConfigItem
from ..models.utils import model_verbose_name

logger = logging.getLogger(__name__)


class MenuEntry:
    """ Base class for entries of main-menu (displayed on top of all pages).

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

    # The label is a human-readable string (generally a gettext_lazy object).
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
    permissions: str | Sequence[str] = ''

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
                 config_item_id: int | None = None,
                 data: dict | None = None,
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

    def check_permissions(self, user: CremeUser) -> None:
        """@raise PermissionDenied."""
        user.has_perms_or_die(self.permissions)

    @property
    def children(self) -> Iterator[MenuEntry]:
        yield from ()

    def render_label(self, context) -> str:
        return self.label

    # TODO: get_context() instead (like form widgets, buttons, etc...)
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

    def render(self, context):
        label = self.render_label(context)

        try:
            self.check_permissions(context['user'])
        except PermissionDenied as e:
            return format_html(
                '<span class="ui-creme-navigation-text-entry forbidden" title="{error}">'
                '{label}'
                '</span>',
                error=str(e), label=label,
            )

        return format_html(
            '<a href="{url}">{label}</a>', url=self.url, label=label,
        )


class CreationEntry(FixedURLEntry):
    """Specialization of FixedURLEntry to redirect to the creation view of an entity class."""
    # Notice that the label, URL & permissions are automatically computed from the model.
    model: type[CremeEntity] = CremeEntity
    label = 'Creation entry'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model = self.model
        self.label = model.creation_label
        self.permissions = auth.build_creation_perm(model)

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
        model = self.model
        self.label = model._meta.verbose_name_plural
        # self.permissions = meta.app_label
        self.permissions = auth.build_list_perm(model)

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

    creation_label = _('Add a URL entry')
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
            '<a href="{url}" target="_blank">{label}</a>',
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
    Currently, (i.e. theme "icecream" & "chantilly") a horizontal line is
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

    class UnRegistrationError(RegistrationError):
        pass

    def __init__(self) -> None:
        self._entry_classes: dict[str, type[MenuEntry]] = {}

    def register(self, *entry_classes: type[MenuEntry]) -> MenuRegistry:
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

            # if hasattr(entry_cls, '_has_perm'):
            #     logger.critical(
            #         'The class %s still defines a method "_has_perm()"; '
            #         'define the new method "check_permissions()" instead.',
            #         entry_cls,
            #     )

        return self

    def unregister(self, *entry_classes: type[MenuEntry]) -> MenuRegistry:
        for entry_cls in entry_classes:
            try:
                del self._entry_classes[entry_cls.id]
            except KeyError as e:
                raise self.UnRegistrationError(
                    f'Invalid entry {entry_cls} (already unregistered?)'
                ) from e

        return self

    def get_class(self, entry_id: str) -> type[MenuEntry] | None:
        return self._entry_classes.get(entry_id)

    @property
    def entry_classes(self) -> Iterator[type[MenuEntry]]:
        yield from self._entry_classes.values()

    def get_entries(self, config_items: Iterable[MenuConfigItem]) -> list[MenuEntry]:
        """Get instances corresponding some MenuConfigItems.
        Parenting is managed ; and attributes 'config_item_id' are filled.
        """
        # NB: 2 lists for 2 levels   TODO: generalise with deeper levels?
        entry_info: list[list[tuple[type[MenuEntry], MenuConfigItem]]] = [[], []]
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

    def __init__(self) -> None:
        self._items = []
        self._ids: set[str] = set()  # IDs of _items, for fast existence checking.

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def add(self, *items, **kwargs) -> _PriorityList:
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
    def __init__(self, id, model: type[CremeEntity] | None = None, **kwargs):
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
            self.label = get('label') or model_verbose_name(model)
            # NB: we cannot call model.get_create_absolute_url() immediately
            #     because the url resolver will be used too soon
            #     (the apps could be not totally initialized).
            self._url = get('url')
            self.perm = get('perm') or auth.build_creation_perm(model)
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
                        'return a URL, or the creation popup will not work correctly',
                        model,
                    )
            else:
                url = str(url)
        else:
            url = str(url)

        return url

    def to_dict(self, user) -> dict[str, str]:
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
        yield from self._links

    def __str__(self):
        return f'<Group: id="{self.id}" label="{self.label}" priority={self._priority}>'

    def change_links_priority(self, priority, *link_ids):
        self._links.change_priority(priority, *link_ids)

    def add_link(self,
                 id: str,
                 model=None,
                 priority=None,
                 **kwargs) -> _CreationViewLinksGroup:
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

    def __iter__(self) -> Iterator[_CreationViewLinksGroup]:
        custom_types = [
            ce_type
            for ce_type in CustomEntityType.objects.all_types()
            if ce_type.enabled
        ]
        if custom_types:
            # TODO: reserve use of this "id"
            custom_group = self._group_class(id='custom_entities', label=_('Custom entities'))
            # TODO: sort by label?
            for priority, ce_type in enumerate(custom_types, start=1):
                custom_group.add_link(
                    id=f'creme_core-create_custom{priority}',
                    model=ce_type.entity_model,
                    priority=priority,
                )

            yield custom_group

        yield from self._groups

    def change_groups_priority(self, priority, *group_ids) -> None:
        """Change the priority of several groups at once.
        See _PriorityList.change_priority().
        """
        self._groups.change_priority(priority, *group_ids)

    def get_or_create_group(self,
                            group_id: str,
                            label,
                            priority=None,
                            ) -> _CreationViewLinksGroup:
        """Get a group of links by its ID, & create it if it does not exist."""
        groups = self._groups

        try:
            group = groups.get(group_id)
        except KeyError:
            group = self._group_class(id=group_id, label=label)
            groups.add(group, priority=priority)

        return group

    def remove_groups(self, *group_ids: str) -> None:
        """Remove several groups at once.
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
