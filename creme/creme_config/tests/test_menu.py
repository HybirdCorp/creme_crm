from functools import partial
from json import dumps as json_dump
from unittest import skipIf

from django.apps import apps
from django.forms import CharField
from django.urls import reverse
from django.utils.functional import partition
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.gui.menu import (
    ContainerEntry,
    CustomURLEntry,
    Separator0Entry,
    Separator1Entry,
    menu_registry,
)
# RecentEntitiesEntry
from creme.creme_core.menu import CremeEntry, LogoutEntry, QuickAccessEntry
from creme.creme_core.models import FakeContact, MenuConfigItem
from creme.creme_core.tests import fake_menu
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.fake_menu import (
    FakeContactCreationEntry,
    FakeContactsEntry,
    FakeOrganisationCreationEntry,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import MenuBrick
from ..forms.fields import MenuEntriesField
from ..menu import (
    BricksConfigEntry,
    ButtonsConfigEntry,
    ConfigPortalEntry,
    CremeConfigEntry,
    CurrentAppConfigEntry,
    CustomEntityTypesConfigEntry,
    CustomFieldsConfigEntry,
    CustomFormsConfigEntry,
    FieldsConfigEntry,
    HistoryConfigEntry,
    MySettingsEntry,
    PropertyTypesConfigEntry,
    RelationTypesConfigEntry,
    RolesConfigEntry,
    SearchConfigEntry,
    TimezoneEntry,
    UsersConfigEntry,
    WorkflowsConfigEntry,
)
from ..views.portal import Portal

if apps.is_installed('creme.persons'):
    from creme.persons import get_contact_model
    from creme.persons.tests.base import skipIfCustomContact
else:
    def skipIfCustomContact(test_func):
        return skipIf(False, '"persons" is not installed')(test_func)


class MenuEntriesTestCase(CremeTestCase):
    def test_tz_entry(self):
        entry = TimezoneEntry()
        self.assertEqual('creme_config-timezone', entry.id)
        self.assertEqual(_("*User's timezone*"),  entry.label)

        tz = 'Europe/Madrid'
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__user_settings'),
                label=_('Time zone: {}').format(tz),
            ),
            entry.render({
                # 'request': self.build_request(user=user),
                'user': self.get_root_user(),
                'TIME_ZONE': tz,
            }),
        )

        # ---
        creme_children = [*CremeEntry().children]

        for child in creme_children:
            if isinstance(child, TimezoneEntry):
                break
        else:
            self.fail(f'No TZ entry found in {creme_children}.')

    def test_my_settings_entry(self):
        entry = MySettingsEntry()
        self.assertEqual('creme_config-my_settings',    entry.id)
        self.assertEqual(_('My settings'),              entry.label)
        self.assertEqual('creme_config__user_settings', entry.url_name)
        self.assertEqual('', entry.permissions)

        # ---
        creme_children = [*CremeEntry().children]

        for child in creme_children:
            if isinstance(child, MySettingsEntry):
                break
        else:
            self.fail(f'No "my setting" entry found in {creme_children}.')

    def test_portal_entry(self):
        entry = ConfigPortalEntry()
        self.assertEqual('creme_config-portal',           entry.id)
        self.assertEqual(_('General configuration'),      entry.label)
        self.assertEqual(reverse('creme_config__portal'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_bricks_entry(self):
        entry = BricksConfigEntry()
        self.assertEqual('creme_config-bricks',           entry.id)
        self.assertEqual(_('Blocks'),                     entry.label)
        self.assertEqual(reverse('creme_config__bricks'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_custom_fields_entry(self):
        entry = CustomFieldsConfigEntry()
        self.assertEqual('creme_config-custom_fields',           entry.id)
        self.assertEqual(_('Custom fields'),                     entry.label)
        self.assertEqual(reverse('creme_config__custom_fields'), entry.url)
        self.assertEqual('creme_config',                         entry.permissions)

    def test_custom_entity_types_entry(self):
        entry = CustomEntityTypesConfigEntry()
        self.assertEqual('creme_config-custom_entities',               entry.id)
        self.assertEqual(_('Custom entities'),                         entry.label)
        self.assertEqual(reverse('creme_config__custom_entity_types'), entry.url)
        self.assertEqual('creme_config',                               entry.permissions)

    def test_fields_entry(self):
        entry = FieldsConfigEntry()
        self.assertEqual('creme_config-fields',           entry.id)
        self.assertEqual(_('Fields'),                     entry.label)
        self.assertEqual(reverse('creme_config__fields'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_custom_forms_entry(self):
        entry = CustomFormsConfigEntry()
        self.assertEqual('creme_config-custom_forms',           entry.id)
        self.assertEqual(_('Custom forms'),                     entry.label)
        self.assertEqual(reverse('creme_config__custom_forms'), entry.url)
        self.assertEqual('creme_config',                        entry.permissions)

    def test_workflows_entry(self):
        entry = WorkflowsConfigEntry()
        self.assertEqual('creme_config-workflows',           entry.id)
        self.assertEqual(_('Workflows'),                     entry.label)
        self.assertEqual(reverse('creme_config__workflows'), entry.url)
        self.assertEqual('creme_config',                     entry.permissions)

    def test_history_entry(self):
        entry = HistoryConfigEntry()
        self.assertEqual('creme_config-history',           entry.id)
        self.assertEqual(_('History'),                     entry.label)
        self.assertEqual(reverse('creme_config__history'), entry.url)
        self.assertEqual('creme_config',                   entry.permissions)

    def test_buttons_entry(self):
        entry = ButtonsConfigEntry()
        self.assertEqual('creme_config-buttons',           entry.id)
        self.assertEqual(_('Button menu'),                 entry.label)
        self.assertEqual(reverse('creme_config__buttons'), entry.url)
        self.assertEqual('creme_config',                   entry.permissions)

    def test_search_entry(self):
        entry = SearchConfigEntry()
        self.assertEqual('creme_config-search',                 entry.id)
        self.assertEqual(pgettext('creme_core-noun', 'Search'), entry.label)
        self.assertEqual(reverse('creme_config__search'),       entry.url)
        self.assertEqual('creme_config',                        entry.permissions)

    def test_roles_entry(self):
        entry = RolesConfigEntry()
        self.assertEqual('creme_config-roles',           entry.id)
        self.assertEqual(_('Roles and credentials'),     entry.label)
        self.assertEqual(reverse('creme_config__roles'), entry.url)
        # self.assertEqual('creme_config',                 entry.permissions)
        self.assertEqual('special#creme_config-role',    entry.permissions)

    def test_property_types_entry(self):
        entry = PropertyTypesConfigEntry()
        self.assertEqual('creme_config-property_types',   entry.id)
        self.assertEqual(_('Types of property'),          entry.label)
        self.assertEqual(reverse('creme_config__ptypes'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_relation_types_entry(self):
        entry = RelationTypesConfigEntry()
        self.assertEqual('creme_config-relation_types',   entry.id)
        self.assertEqual(_('Types of relationship'),      entry.label)
        self.assertEqual(reverse('creme_config__rtypes'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_users_entry(self):
        entry = UsersConfigEntry()
        self.assertEqual('creme_config-users',           entry.id)
        self.assertEqual(_('Users'),                     entry.label)
        self.assertEqual(reverse('creme_config__users'), entry.url)
        # self.assertEqual('creme_config',                 entry.permissions)
        self.assertEqual('special#creme_config-user',    entry.permissions)

    def test_current_app_entry01(self):
        user = self.login_as_root_and_get()

        entry = CurrentAppConfigEntry()
        self.assertEqual('creme_config-current_app',    entry.id)
        self.assertEqual(_("*Current app's settings*"), entry.label)

        self.assertEqual(
            '',
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

        fake_contact = FakeContact.objects.create(user=user, last_name='Doe')
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__app_portal', args=('creme_core',)),
                label=_('Configuration of «{app}»').format(app=_('Core')),
            ),
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
                'object': fake_contact,
            }),
        )

    @skipIfCustomContact
    def test_current_app_entry02(self):
        "Other app."
        user = self.login_as_standard(admin_4_apps=('persons',))

        contact = get_contact_model().objects.create(user=user, last_name='Doe')
        expected = '<a href="{url}">{label}</a>'.format(
            url=reverse('creme_config__app_portal', args=('persons',)),
            label=_('Configuration of «{app}»').format(
                app=_('Accounts and Contacts'),
            ),
        )
        render = CurrentAppConfigEntry().render
        self.assertHTMLEqual(
            expected,
            render({'user': user, 'object': contact}),
        )

        # ---
        from creme.persons.views.contact import ContactsList
        self.assertHTMLEqual(
            expected,
            render({'user': user, 'view': ContactsList()}),
        )

    @skipIfCustomContact
    def test_current_app_entry03(self):
        "Not allowed"
        user = self.login_as_standard()

        contact = get_contact_model().objects.create(user=user, last_name='Doe')
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">{}</span>'.format(
                escape(_('Configuration of «{app}»').format(
                    app=_('Accounts and Contacts'),
                )),
            ),
            CurrentAppConfigEntry().render({
                'user': user,
                'object': contact,
            }),
        )

    @skipIfNotInstalled('creme.activities')
    def test_current_app_entry04(self):
        "View without model."
        from creme.activities.views.calendar import CalendarView

        user = self.login_as_root_and_get()

        view = CalendarView()
        self.assertHasNoAttr(view, 'model')
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__app_portal', args=('activities',)),
                label=_('Configuration of «{app}»').format(
                    app=_('Activities'),
                ),
            ),
            CurrentAppConfigEntry().render({'user': user, 'view': view}),
        )

    def test_current_app_entry05(self):
        "creme_config's view."
        user = self.login_as_root_and_get()

        self.assertFalse(
            CurrentAppConfigEntry().render({'user': user, 'view': Portal()}),
        )

    def test_config_entry(self):
        user = self.login_as_root_and_get()

        entry = CremeConfigEntry()
        self.assertEqual(0, entry.level)
        self.assertTrue(entry.is_required)
        self.assertTrue(entry.single_instance)
        self.assertFalse(entry.accepts_children)

        entry_id = 'creme_config-main'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Configuration')
        self.assertEqual(entry_label, entry.label)

        context = {
            'request': self.build_request(user=user),
            'user': user,
            # 'THEME_NAME': 'icecream',
        }

        render = entry.render(context)
        self.assertStartsWith(
            render,
            '<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">'
        )

        ul_node = self.get_html_node_or_fail(self.get_html_tree(render), './/ul')

        links = []
        for li_node in ul_node.findall('li'):
            links.extend(
                (a_node.get('href'), a_node.text)
                for a_node in li_node.findall('.//a')
            )

        self.maxDiff = None
        self.assertListEqual(
            [
                (reverse('creme_config__portal'),              _('General configuration')),
                (reverse('creme_config__world_settings'),      _('Instance')),
                (reverse('creme_config__bricks'),              _('Blocks')),
                (reverse('creme_config__custom_fields'),       _('Custom fields')),
                (reverse('creme_config__custom_entity_types'), _('Custom entities')),
                (reverse('creme_config__fields'),              _('Fields')),
                (reverse('creme_config__custom_forms'),        _('Custom forms')),
                (reverse('creme_config__workflows'),           _('Workflows')),
                (reverse('creme_config__history'),             _('History')),
                (reverse('creme_config__menu'),                _('Menu')),
                (reverse('creme_config__notification'),        _('Notifications')),
                (reverse('creme_config__buttons'),             _('Button menu')),
                (reverse('creme_config__search'), pgettext('creme_core-noun', 'Search')),
                (reverse('creme_config__ptypes'),              _('Types of property')),
                (reverse('creme_config__rtypes'),              _('Types of relationship')),
                (reverse('creme_config__users'),               _('Users')),
                (reverse('creme_config__roles'),               _('Roles and credentials')),
                (reverse('creme_config__efilters'),            _('Filters')),
                (reverse('creme_config__hfilters'),            _('Views')),
            ],
            links,
        )

        # TODO: check presence of CurrentAppConfigEntry

    def test_global_registry(self):
        self.assertIn(CremeConfigEntry, menu_registry.entry_classes)


class MenuConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__menu')
    DELETE_URL = reverse('creme_config__delete_menu_level0')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._items_backup = [*MenuConfigItem.objects.all()]
        MenuConfigItem.objects.all().delete()

        cls.role = cls.get_regular_role()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        MenuConfigItem.objects.all().delete()

        create_items = MenuConfigItem.objects.bulk_create
        child_items, parent_items = partition(
            (lambda item: item.parent_id is None),
            cls._items_backup,
        )

        try:
            create_items(parent_items)
            create_items(child_items)
        except Exception as e:
            print(f'{cls.__name__}: test-data backup problem ({e})')

    def _assert_item_in(self, entry_id, items, **kwargs):
        for item in items:
            if item.entry_id == entry_id:
                for attr_name, attr_value in kwargs.items():
                    value = getattr(item, attr_name)

                    if attr_value != value:
                        self.fail(
                            f'The entry with entry_id="{entry_id}" has been found, '
                            f'but attribute "{attr_name}" is {value!r} '
                            f'(expected {attr_value!r}).'
                        )

                return item

        self.fail(f'Item not found with entry_id="{entry_id}"')

    @staticmethod
    def _build_add_container_url(role=None, superuser=False):
        return reverse(
            'creme_config__add_menu_container',
            args=(
                'superuser' if superuser else role.id if role else 'default',
            ),
        )

    @staticmethod
    def _build_edit_container_url(item):
        return reverse('creme_config__edit_menu_container', args=(item.id,))

    @staticmethod
    def _build_special_level0_url(role=None, superuser=False):
        return reverse(
            'creme_config__add_menu_special_level0',
            args=(
                'superuser' if superuser else role.id if role else 'default',
            ),
        )

    @staticmethod
    def _build_special_level1_url(entry_id):
        return reverse('creme_config__add_menu_special_level1', args=(entry_id,))

    @staticmethod
    def _build_reorder_level0_url(item):
        return reverse(
            'creme_config__reorder_menu_level0',
            args=(
                'superuser' if item.superuser else (item.role_id or 'default'),
                item.id,
            ),
        )

    def _build_simple_menu(self, role=None, superuser=False):
        create_mitem = partial(
            MenuConfigItem.objects.create, role=role, superuser=superuser,
        )
        create_mitem(entry_id=CremeEntry.id,      order=1)
        create_mitem(entry_id=Separator0Entry.id, order=2)

        container = create_mitem(
            entry_id=ContainerEntry.id, entry_data={'label': 'Directory'}, order=3,
        )
        create_mitem(
            entry_id=fake_menu.FakeContactsEntry.id,      order=1, parent=container,
        )
        create_mitem(
            entry_id=fake_menu.FakeOrganisationsEntry.id, order=2, parent=container,
        )

    def test_portal01(self):
        "Only default menu."
        self.login_as_root()
        self._build_simple_menu()

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/menu.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/menu-config.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(self.get_html_tree(response.content), brick=MenuBrick)
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Configured menu',
            plural_title='{count} Configured menus',
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node),
            url=reverse('creme_config__clone_menu'), label=_('New menu for a role'),
        )

    def test_portal02(self):
        self.login_as_root()
        role1 = self.role

        self._build_simple_menu()
        self._build_simple_menu(role=role1)
        self._build_simple_menu(superuser=True)

        response = self.assertGET200(self.PORTAL_URL)
        brick_node = self.get_brick_node(self.get_html_tree(response.content), brick=MenuBrick)
        self.assertBrickTitleEqual(
            brick_node,
            count=3,
            title='{count} Configured menu',
            plural_title='{count} Configured menus',
        )
        self.assertBrickHeaderHasNoButton(
            self.get_brick_header_buttons(brick_node),
            url=reverse('creme_config__clone_menu'),
        )

    def test_add_special_level1_entry01(self):
        "Separator1."
        self.login_as_root()

        entry_id = Separator1Entry.id
        url = self._build_special_level1_url(entry_id)
        response1 = self.assertGET200(url)
        ctxt1 = response1.context
        self.assertEqual(_('Add a separator'), ctxt1.get('title'))
        self.assertEqual(_('Add this entry'),  ctxt1.get('submit_label'))

        with self.assertNoException():
            fields = ctxt1['form'].fields
            label_f = fields['label']

        self.assertEqual(1, len(fields))
        self.assertFalse(label_f.required)

        # ---
        label = 'Important'
        response2 = self.assertPOST200(url, data={'label': label})
        self.assertListEqual(
            [{'label': label, 'value': {'id': entry_id, 'data': {'label': label}}}],
            response2.json(),
        )

        # ---
        response3 = self.assertPOST200(url, data={'label': ''})
        self.assertListEqual(
            [{'label': '', 'value': {'id': entry_id, 'data': {'label': ''}}}],
            response3.json(),
        )

    def test_add_special_level1_entry02(self):
        "Custom URL."
        self.login_as_root()

        entry_id = CustomURLEntry.id
        url = self._build_special_level1_url(entry_id)
        ctxt1 = self.assertGET200(url).context
        self.assertEqual(_('Add a URL entry'), ctxt1.get('title'))

        with self.assertNoException():
            fields = ctxt1['form'].fields
            label_f = fields['label']
            url_f = fields['url']

        self.assertTrue(label_f.required)
        self.assertTrue(url_f.required)

        # ---
        label = 'Wiki'
        entry_url = 'https://my.wiki.org'
        response2 = self.assertPOST200(url, data={'label': label, 'url': entry_url})
        self.assertListEqual(
            [
                {
                    'label': label,
                    'value': {'id': entry_id, 'data': {'label': label, 'url': entry_url}},
                }
            ],
            response2.json(),
        )

        # ---
        response3 = self.client.post(url, data={'label': label, 'url': 'invalid_url'})
        self.assertFormError(
            response3.context['form'],
            field='url', errors=_('Enter a valid URL.'),
        )

    def test_add_special_level1_entry03(self):
        "Invalid entries."
        self.login_as_root()

        build_url = self._build_special_level1_url
        self.assertGET404(build_url('invalid'))
        self.assertGET404(build_url(CremeEntry.id))
        self.assertGET404(build_url(FakeContactCreationEntry.id))

    def test_add_container01(self):
        "Default configuration."
        self.login_as_root()

        url = self._build_add_container_url()
        response1 = self.assertGET200(url)
        ctxt1 = response1.context
        self.assertEqual(_('Add a container of entries'), ctxt1.get('title'))

        with self.assertNoException():
            fields = ctxt1['form'].fields
            label_f = fields['label']
            entries_f = fields['entries']

        self.assertIsInstance(label_f, CharField)
        self.assertEqual(50, label_f.max_length)

        self.assertIsInstance(entries_f, MenuEntriesField)
        self.assertFalse([*entries_f.excluded_entry_ids])
        self.assertListEqual([], entries_f.initial)

        label01 = 'Fake Contacts'
        response2 = self.client.post(
            url,
            data={
                'label': label01,

                'entries': json_dump([
                    {'id': FakeContactsEntry.id},
                    {'id': FakeContactCreationEntry.id},
                ]),
            },
        )
        self.assertNoFormError(response2)

        items01 = [*MenuConfigItem.objects.order_by('id')]
        self.assertEqual(3, len(items01))

        container01 = items01[0]
        self.assertEqual('creme_core-container', container01.entry_id)
        self.assertEqual(0,                      container01.order)
        self.assertDictEqual({'label': label01}, container01.entry_data)
        self.assertIsNone(container01.parent)
        self.assertIsNone(container01.role)
        self.assertFalse(container01.superuser)

        sub_item11 = items01[1]
        self.assertEqual(FakeContactsEntry.id, sub_item11.entry_id)
        self.assertEqual(0,                    sub_item11.order)
        self.assertEqual(container01.id,       sub_item11.parent_id)
        self.assertDictEqual({}, sub_item11.entry_data)
        self.assertIsNone(sub_item11.role)
        self.assertFalse(sub_item11.superuser)

        sub_item12 = items01[2]
        self.assertEqual(FakeContactCreationEntry.id, sub_item12.entry_id)
        self.assertEqual(1,                           sub_item12.order)
        self.assertEqual(container01.id,              sub_item12.parent_id)
        self.assertDictEqual({}, sub_item12.entry_data)

    def test_add_container02(self):
        "There are already containers."
        self.login_as_root()
        role = self.role

        create_item = MenuConfigItem.objects.create
        creme_item = create_item(entry_id=CremeEntry.id, order=0)
        # NB: notice order is not 1 => our new container must have order=11
        container1 = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My organisations'},
            order=10,
        )
        sub_item11 = create_item(entry_id=FakeContactsEntry.id,        order=0, parent=container1)
        sub_item12 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container1)

        # Should be ignored
        super_container = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My super organisations'},
            order=1,
            superuser=True,
        )
        super_item = create_item(
            entry_id=FakeOrganisationCreationEntry.id, order=0, parent=super_container,
            superuser=True,
        )
        role_container = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My role organisations'},
            order=1,
            role=role,
        )
        role_item = create_item(
            entry_id=FakeOrganisationCreationEntry.id, order=0, parent=role_container,
            role=role,
        )

        url = self._build_add_container_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            entries_f = response1.context['form'].fields['entries']

        excluded_entry_ids = [*entries_f.excluded_entry_ids]
        self.assertIn(FakeContactsEntry.id,        excluded_entry_ids)
        self.assertIn(FakeContactCreationEntry.id, excluded_entry_ids)
        self.assertNotIn(FakeOrganisationCreationEntry.id, excluded_entry_ids)

        label = 'Fake Organisations'
        response2 = self.client.post(
            url,
            data={
                'label': label,
                'entries': json_dump([
                    {'id': FakeOrganisationCreationEntry.id},
                ]),
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(
            6, MenuConfigItem.objects.filter(superuser=False, role=None).count(),
        )

        items = [
            *MenuConfigItem.objects.exclude(id__in=[
                creme_item.id, container1.id, sub_item11.id, sub_item12.id,
                super_container.id, super_item.id,
                role_container.id, role_item.id,
            ]),
        ]
        self.assertEqual(2, len(items))

        with self.assertNoException():
            container2 = next(
                item for item in items if item.entry_id == 'creme_core-container'
            )
        self.assertEqual(11, container2.order)
        self.assertDictEqual({'label': label}, container2.entry_data)

        sub_item21 = next(item for item in items if item is not container2)
        self.assertEqual(FakeOrganisationCreationEntry.id, sub_item21.entry_id)
        self.assertEqual(0,                                sub_item21.order)
        self.assertEqual(container2.id,                    sub_item21.parent_id)
        self.assertDictEqual({}, sub_item21.entry_data)

    def test_add_container03(self):
        "Superuser configuration."
        self.login_as_root()

        label = 'Fake Directory'
        response = self.client.post(
            self._build_add_container_url(superuser=True),
            data={
                'label': label,
                'entries': json_dump([{'id': FakeContactsEntry.id}]),
            },
        )
        self.assertNoFormError(response)

        items = [*MenuConfigItem.objects.order_by('id')]
        self.assertEqual(2, len(items))

        container = items[0]
        self.assertEqual('creme_core-container', container.entry_id)
        self.assertEqual(0,                      container.order)
        self.assertDictEqual({'label': label}, container.entry_data)
        self.assertIsNone(container.parent)
        self.assertIsNone(container.role)
        self.assertTrue(container.superuser)

        sub_item = items[1]
        self.assertEqual(FakeContactsEntry.id, sub_item.entry_id)
        self.assertEqual(0,                    sub_item.order)
        self.assertEqual(container.id,         sub_item.parent_id)
        self.assertDictEqual({}, sub_item.entry_data)
        self.assertIsNone(sub_item.role)
        self.assertTrue(sub_item.superuser)

    def test_add_container04(self):
        "Role configuration."
        self.login_as_root()

        role = self.role
        label = 'Fake Directory'
        response = self.client.post(
            self._build_add_container_url(role=role),
            data={
                'label': label,
                'entries': json_dump([{'id': FakeContactsEntry.id}]),
            },
        )
        self.assertNoFormError(response)

        items = [*MenuConfigItem.objects.order_by('id')]
        self.assertEqual(2, len(items))

        container = items[0]
        self.assertEqual('creme_core-container', container.entry_id)
        self.assertEqual(0,                      container.order)
        self.assertDictEqual({'label': label}, container.entry_data)
        self.assertIsNone(container.parent)
        self.assertFalse(container.superuser)
        self.assertEqual(role, container.role)

        sub_item = items[1]
        self.assertEqual(FakeContactsEntry.id, sub_item.entry_id)
        self.assertEqual(0,                    sub_item.order)
        self.assertEqual(container.id,         sub_item.parent_id)
        self.assertDictEqual({}, sub_item.entry_data)
        self.assertFalse(sub_item.superuser)
        self.assertEqual(role, sub_item.role)

    def test_add_special_level0_entry01(self):
        "Add CremeEntry (one instance max)."
        self.login_as_root()

        url = self._build_special_level0_url()
        ctxt1 = self.assertGET200(url).context
        self.assertEqual(_('Add a special root entry'), ctxt1['title'])

        with self.assertNoException():
            choices1 = ctxt1['form'].fields['entry_id'].choices

        self.assertInChoices(
            value=CremeEntry.id, label=CremeEntry.label, choices=choices1,
        )
        self.assertInChoices(
            # value=RecentEntitiesEntry.id, label=RecentEntitiesEntry.label,
            value=QuickAccessEntry.id, label=QuickAccessEntry.label,
            choices=choices1,
        )
        self.assertInChoices(
            value=Separator0Entry.id, label=Separator0Entry.label,
            choices=choices1,
        )
        self.assertNotInChoices(value=ContainerEntry.id, choices=choices1)
        self.assertNotInChoices(value=LogoutEntry.id,    choices=choices1)

        entry_id = CremeEntry.id
        response2 = self.client.post(url, data={'entry_id': entry_id})
        self.assertNoFormError(response2)

        special_item = self.get_alone_element(MenuConfigItem.objects.all())
        self.assertEqual('creme_core-creme', special_item.entry_id)
        self.assertEqual(0,                  special_item.order)
        self.assertDictEqual({}, special_item.entry_data)
        self.assertIsNone(special_item.parent)
        self.assertFalse(special_item.superuser)
        self.assertIsNone(special_item.role)

        # ---
        response3 = self.assertGET200(url)

        with self.assertNoException():
            choices02 = response3.context['form'].fields['entry_id'].choices

        self.assertNotInChoices(value=CremeEntry.id, choices=choices02)

    def test_add_special_level0_entry02(self):
        "With existing items."
        self.login_as_root()

        url = self._build_special_level0_url()

        # Order of next container should be 21
        create_item = MenuConfigItem.objects.create
        special_item1 = create_item(entry_id=CremeEntry.id, order=10)
        container = create_item(entry_id=ContainerEntry.id, order=20)
        item = create_item(entry_id=FakeContactsEntry.id, parent=container, order=0)

        response1 = self.assertGET200(url)

        with self.assertNoException():
            choices02 = response1.context['form'].fields['entry_id'].choices

        self.assertInChoices(
            # value=RecentEntitiesEntry.id, label=RecentEntitiesEntry.label,
            value=QuickAccessEntry.id, label=QuickAccessEntry.label,
            choices=choices02,
        )
        self.assertNotInChoices(value=CremeEntry.id, choices=choices02)

        # entry_id = RecentEntitiesEntry.id
        entry_id = QuickAccessEntry.id
        response2 = self.client.post(url, data={'entry_id': entry_id})
        self.assertNoFormError(response2)

        self.assertEqual(4, MenuConfigItem.objects.count())

        special_item2 = self.get_alone_element(MenuConfigItem.objects.exclude(
            id__in=[special_item1.id, container.id, item.id],
        ))
        self.assertEqual('creme_core-recent_entities', special_item2.entry_id)
        self.assertEqual(21, special_item2.order)

    def test_add_special_level0_entry03(self):
        "Separator0 can have several instances."
        self.login_as_root()
        MenuConfigItem.objects.create(entry_id=Separator0Entry.id, order=1)

        response = self.assertGET200(self._build_special_level0_url())

        with self.assertNoException():
            choices = response.context['form'].fields['entry_id'].choices

        self.assertInChoices(
            value=Separator0Entry.id, label=Separator0Entry.label,
            choices=choices,
        )

    def test_add_special_level0_entry04(self):
        "Superuser configuration."
        self.login_as_root()

        url = self._build_special_level0_url(superuser=True)

        entry_id = CremeEntry.id
        self.assertNoFormError(self.client.post(url, data={'entry_id': entry_id}))

        special_item = self.get_alone_element(MenuConfigItem.objects.all())
        self.assertEqual('creme_core-creme', special_item.entry_id)
        self.assertEqual(0,                  special_item.order)
        self.assertDictEqual({}, special_item.entry_data)
        self.assertIsNone(special_item.parent)
        self.assertIsNone(special_item.role)
        self.assertTrue(special_item.superuser)

        # ---
        response2 = self.assertGET200(url)

        with self.assertNoException():
            choices2 = response2.context['form'].fields['entry_id'].choices

        self.assertNotInChoices(value=CremeEntry.id, choices=choices2)

        # ---
        response3 = self.assertGET200(self._build_special_level0_url())

        with self.assertNoException():
            choices3 = response3.context['form'].fields['entry_id'].choices

        self.assertInChoices(
            value=CremeEntry.id, label=CremeEntry.label, choices=choices3,
        )

    def test_add_special_level0_entry05(self):
        "Superuser configuration."
        self.login_as_root()
        role = self.role
        url = self._build_special_level0_url(role=role)

        entry_id = CremeEntry.id
        self.assertNoFormError(self.client.post(url, data={'entry_id': entry_id}))

        special_item = self.get_alone_element(MenuConfigItem.objects.all())
        self.assertEqual('creme_core-creme', special_item.entry_id)
        self.assertEqual(0,                  special_item.order)
        self.assertDictEqual({}, special_item.entry_data)
        self.assertIsNone(special_item.parent)
        self.assertFalse(special_item.superuser)
        self.assertEqual(role, special_item.role)

        # ---
        response2 = self.assertGET200(url)

        with self.assertNoException():
            choices2 = response2.context['form'].fields['entry_id'].choices

        self.assertNotInChoices(value=CremeEntry.id, choices=choices2)

        # ---
        response3 = self.assertGET200(self._build_special_level0_url())

        with self.assertNoException():
            choices3 = response3.context['form'].fields['entry_id'].choices

        self.assertInChoices(
            value=CremeEntry.id, label=CremeEntry.label, choices=choices3,
        )

    def test_edit_container01(self):
        "New items added."
        self.login_as_root()
        role = self.role

        label = 'my contacts'
        create_item = MenuConfigItem.objects.create
        container1 = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My organisations'},
            order=0,
        )
        container2 = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': label},
            order=1,
        )
        create_item(entry_id=FakeOrganisationCreationEntry.id, order=0, parent=container1)
        sub_item21 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container2)

        # Should be ignored
        super_container = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My super contact'},
            order=1,
            superuser=True,
        )
        create_item(
            entry_id=FakeContactsEntry.id, order=0, parent=super_container,
            superuser=True,
        )
        role_container = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': 'My role organisations'},
            order=1,
            role=role,
        )
        create_item(
            entry_id=FakeContactsEntry.id, order=0, parent=role_container,
            role=role,
        )

        url = self._build_edit_container_url(container2)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the container «{object}»').format(object=label),
            context.get('title'),
        )

        with self.assertNoException():
            fields = context['form'].fields
            label_f = fields['label']
            entries_f = fields['entries']

        self.assertEqual(label, label_f.initial)
        self.assertIsInstance(entries_f, MenuEntriesField)

        excluded_entry_ids = [*entries_f.excluded_entry_ids]
        self.assertIn(FakeOrganisationCreationEntry.id, excluded_entry_ids)
        self.assertNotIn(FakeContactsEntry.id, excluded_entry_ids)

        initial_entries = entries_f.initial
        self.assertIsList(initial_entries, length=1)

        initial_entry1 = initial_entries[0]
        self.assertIsInstance(initial_entry1, FakeContactsEntry)
        self.assertEqual(FakeContact._meta.verbose_name_plural, initial_entry1.label)

        edited_label = label.title()
        response2 = self.client.post(
            url,
            data={
                'label': edited_label,
                'entries': json_dump([
                    {'id': FakeContactsEntry.id},
                    {'id': FakeContactCreationEntry.id},
                ]),
            },
        )
        self.assertNoFormError(response2)

        container2 = self.refresh(container2)
        self.assertDictEqual({'label': edited_label}, container2.entry_data)

        sub_item21 = self.refresh(sub_item21)
        self.assertEqual(FakeContactsEntry.id, sub_item21.entry_id)
        self.assertEqual(container2.id,        sub_item21.parent_id)
        self.assertEqual(0,                    sub_item21.order)
        self.assertDictEqual({}, sub_item21.entry_data)

        sub_item22 = self.get_object_or_fail(
            MenuConfigItem, entry_id=FakeContactCreationEntry.id,
        )
        self.assertEqual(container2.id, sub_item22.parent_id)
        self.assertEqual(1,             sub_item22.order)
        self.assertDictEqual({}, sub_item22.entry_data)

    def test_edit_container02(self):
        "Some items removed, some changed."
        self.login_as_root()

        label = 'My contacts'
        create_item = MenuConfigItem.objects.create
        container = create_item(
            entry_id=ContainerEntry.id, entry_data={'label': label}, order=0,
        )
        sub_item1 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container)
        sub_item2 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container)

        response2 = self.client.post(
            self._build_edit_container_url(container),
            data={
                'label': label,
                'entries': json_dump([
                    {'id': FakeContactCreationEntry.id},
                ]),
            },
        )
        self.assertNoFormError(response2)

        sub_item1 = self.refresh(sub_item1)
        self.assertEqual(0,                           sub_item1.order)
        self.assertEqual(FakeContactCreationEntry.id, sub_item1.entry_id)
        self.assertEqual(container.id,                sub_item1.parent_id)
        self.assertDictEqual({}, sub_item1.entry_data)

        self.assertDoesNotExist(sub_item2)

    def test_edit_container03(self):
        "Items with label/data."
        self.login_as_root()

        label = 'My contacts'
        create_item = MenuConfigItem.objects.create
        container = create_item(
            entry_id=ContainerEntry.id, entry_data={'label': label}, order=0,
        )
        sub_item1 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container)

        sep_label = 'My sites'
        cust_label = 'Home page'
        cust_url = 'http://my.home.page.com'
        response2 = self.client.post(
            self._build_edit_container_url(container),
            data={
                'label': label,
                'entries': json_dump([
                    {'id': Separator1Entry.id, 'data': {'label': sep_label}},
                    {'id': CustomURLEntry.id, 'data': {'label': cust_label, 'url': cust_url}},
                ]),
            },
        )
        self.assertNoFormError(response2)

        sub_item1 = self.refresh(sub_item1)
        self.assertEqual(Separator1Entry.id, sub_item1.entry_id)
        self.assertEqual(container.id,       sub_item1.parent_id)
        self.assertEqual(0,                  sub_item1.order)
        self.assertDictEqual({'label': sep_label}, sub_item1.entry_data)

        sub_item2 = self.get_object_or_fail(
            MenuConfigItem, entry_id=CustomURLEntry.id,
        )
        self.assertEqual(container.id, sub_item2.parent_id)
        self.assertEqual(1,            sub_item2.order)
        self.assertDictEqual(
            {'label': cust_label, 'url': cust_url}, sub_item2.entry_data,
        )

    def test_edit_container_error(self):
        self.login_as_root()

        create_item = MenuConfigItem.objects.create
        item01 = create_item(entry_id=CremeEntry.id, order=0)
        self.assertGET404(self._build_edit_container_url(item01))

        # item02 = create_item(entry_id=RecentEntitiesEntry.id, order=0)
        item02 = create_item(entry_id=QuickAccessEntry.id, order=0)
        self.assertGET404(self._build_edit_container_url(item02))

    def test_remove_container01(self):
        self.login_as_root()

        create_item = MenuConfigItem.objects.create
        container = create_item(
            entry_id=ContainerEntry.id, entry_data={'label': 'My contacts'}, order=0,
        )
        sub_item1 = create_item(entry_id=FakeContactsEntry.id,        order=0, parent=container)
        sub_item2 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container)

        url = self.DELETE_URL
        self.assertGET405(url)

        self.assertPOST200(url, data={'id': container.id})
        self.assertDoesNotExist(container)
        self.assertDoesNotExist(sub_item1)
        self.assertDoesNotExist(sub_item2)

    def test_remove_container02(self):
        self.login_as_root()

        # item = MenuConfigItem.objects.create(entry_id=RecentEntitiesEntry.id, order=0)
        item = MenuConfigItem.objects.create(entry_id=QuickAccessEntry.id, order=0)
        self.assertPOST200(self.DELETE_URL, data={'id': item.id})
        self.assertDoesNotExist(item)

    def test_remove_container_errors(self):
        self.login_as_root()

        create_item = MenuConfigItem.objects.create
        url = reverse('creme_config__delete_menu_level0')

        # Required container
        item01 = create_item(entry_id=CremeEntry.id, order=0)
        self.assertPOST409(url, data={'id': item01.id})

        # Not container
        item02 = create_item(entry_id=FakeContactsEntry.id, order=0)
        self.assertPOST409(url, data={'id': item02.id})

    def test_reorder_level0_entry01(self):
        "Default configuration."
        self.login_as_standard(admin_4_apps=('creme_core',))

        create_item = MenuConfigItem.objects.create
        item01 = create_item(entry_id=CremeEntry.id, order=1)
        item02 = create_item(
            entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Directory'},
        )
        item03 = create_item(
            entry_id=ContainerEntry.id, order=3, entry_data={'label': 'Activities'},
        )

        sub_item21 = create_item(entry_id=FakeContactsEntry.id,        parent=item02, order=1)
        sub_item22 = create_item(entry_id=FakeContactCreationEntry.id, parent=item02, order=2)

        # Should be ignored
        super_item = create_item(
            entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Super directory'},
            superuser=True,
        )
        role_item = create_item(
            entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Role directory'},
            role=self.role,
        )

        url = self._build_reorder_level0_url(item01)
        self.assertGET405(url)

        self.assertPOST200(url, data={'target': 2})
        self.assertEqual(2, self.refresh(item01).order)
        self.assertEqual(1, self.refresh(item02).order)
        self.assertEqual(3, self.refresh(item03).order)

        self.assertEqual(1, self.refresh(sub_item21).order)
        self.assertEqual(2, self.refresh(sub_item22).order)

        self.assertEqual(2, self.refresh(super_item).order)
        self.assertEqual(2, self.refresh(role_item).order)

    def test_reorder_level0_entry02(self):
        "Not allowed."
        self.login_as_standard()  # admin_4_apps=['creme_core']

        create_item = MenuConfigItem.objects.create
        item01 = create_item(entry_id=CremeEntry.id, order=1)
        create_item(entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Misc'})

        self.assertPOST403(
            self._build_reorder_level0_url(item01),
            data={'target': 2},
        )

    def test_reorder_level0_entry03(self):
        "Superuser configuration."
        self.login_as_standard(admin_4_apps=('creme_core',))

        create_item = partial(MenuConfigItem.objects.create, superuser=True)
        item01 = create_item(entry_id=CremeEntry.id, order=1)
        item02 = create_item(
            entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Directory'},
        )
        item03 = create_item(
            entry_id=ContainerEntry.id, order=3, entry_data={'label': 'Activities'},
        )

        url = self._build_reorder_level0_url(item01)
        self.assertPOST200(url, data={'target': 2})
        self.assertEqual(2, self.refresh(item01).order)
        self.assertEqual(1, self.refresh(item02).order)
        self.assertEqual(3, self.refresh(item03).order)

    def test_reorder_level0_entry04(self):
        "Role configuration."
        user = self.login_as_standard(admin_4_apps=['creme_core'])
        role = user.role

        create_item = partial(MenuConfigItem.objects.create, role=role)
        item01 = create_item(entry_id=CremeEntry.id, order=1)
        item02 = create_item(
            entry_id=ContainerEntry.id, order=2, entry_data={'label': 'Directory'},
        )
        item03 = create_item(
            entry_id=ContainerEntry.id, order=3, entry_data={'label': 'Activities'},
        )

        url = self._build_reorder_level0_url(item01)
        self.assertPOST200(url, data={'target': 2})
        self.assertEqual(2, self.refresh(item01).order)
        self.assertEqual(1, self.refresh(item02).order)
        self.assertEqual(3, self.refresh(item03).order)

    def test_clone01(self):
        "For super-user."
        user = self.login_as_standard(admin_4_apps=['creme_core'])
        role1 = user.role
        role2 = self.create_role(name='Salesman')

        self._build_simple_menu()

        url = reverse('creme_config__clone_menu')
        response1 = self.assertGET200(url)
        ctxt1 = response1.context
        self.assertEqual(_('Create the menu'), ctxt1.get('submit_label'))

        with self.assertNoException():
            role_f1 = ctxt1['form'].fields['role']
            choices1 = role_f1.choices

        self.assertInChoices(value=role1.id, label=role1.name, choices=choices1)
        self.assertInChoices(value=role2.id, label=role2.name, choices=choices1)
        self.assertEqual('*{}*'.format(_('Superuser')), role_f1.empty_label)

        # ---
        response2 = self.client.post(url, data={'role': ''})
        self.assertNoFormError(response2)
        self.assertEqual(10, MenuConfigItem.objects.count())

        new_items = MenuConfigItem.objects.filter(superuser=True, role=None)
        self.assertEqual(5, len(new_items))

        self._assert_item_in(entry_id=CremeEntry.id,      items=new_items, order=1, parent=None)
        self._assert_item_in(entry_id=Separator0Entry.id, items=new_items, order=2, parent=None)

        new_container = self._assert_item_in(
            entry_id=ContainerEntry.id, items=new_items,
            order=3, parent=None, entry_data={'label': 'Directory'},
        )
        self._assert_item_in(
            entry_id=fake_menu.FakeContactsEntry.id, items=new_items,
            order=1, parent_id=new_container.id,
        )
        self._assert_item_in(
            entry_id=fake_menu.FakeOrganisationsEntry.id, items=new_items,
            order=2, parent_id=new_container.id,
        )

        # ---
        response3 = self.assertGET200(url)

        with self.assertNoException():
            role_f2 = response3.context['form'].fields['role']
            choices2 = role_f2.choices

        self.assertInChoices(value=role1.id, label=role1.name, choices=choices2)
        self.assertInChoices(value=role2.id, label=role2.name, choices=choices2)
        self.assertIsNone(role_f2.empty_label)

    def test_clone02(self):
        "For role."
        user = self.login_as_standard(admin_4_apps=('creme_core',))
        role1 = user.role

        self._build_simple_menu()

        url = reverse('creme_config__clone_menu')
        self.assertNoFormError(self.client.post(url, data={'role': role1.id}))
        self.assertEqual(10, MenuConfigItem.objects.count())

        new_items = MenuConfigItem.objects.filter(role=role1, superuser=False)
        self.assertEqual(5, len(new_items))

        self._assert_item_in(entry_id=CremeEntry.id,      items=new_items, order=1, parent=None)
        self._assert_item_in(entry_id=Separator0Entry.id, items=new_items, order=2, parent=None)

        new_container = self._assert_item_in(
            entry_id=ContainerEntry.id, items=new_items,
            order=3, parent=None, entry_data={'label': 'Directory'},
        )
        self._assert_item_in(
            entry_id=fake_menu.FakeContactsEntry.id, items=new_items,
            order=1, parent_id=new_container.id,
        )
        self._assert_item_in(
            entry_id=fake_menu.FakeOrganisationsEntry.id, items=new_items,
            order=2, parent_id=new_container.id,
        )

        # ---
        role2 = self.create_role(name='Salesman')
        response2 = self.assertGET200(url)

        with self.assertNoException():
            role_f = response2.context['form'].fields['role']
            choices = role_f.choices

        self.assertInChoices(value=role2.id, label=role2.name, choices=choices)
        self.assertNotInChoices(value=role1.id, choices=choices)
        self.assertTrue(role_f.empty_label)

        self.assertNoFormError(self.client.post(url, data={'role': role2.id}))
        self.assertEqual(15, MenuConfigItem.objects.count())
        self.assertEqual(
            5, MenuConfigItem.objects.filter(role=role2, superuser=False).count(),
        )

    def test_delete_menu(self):
        user = self.login_as_standard(admin_4_apps=('creme_core',))
        role1 = user.role
        role2 = self.create_role(name='Salesman')

        self._build_simple_menu()
        self._build_simple_menu(role=role1)
        self._build_simple_menu(role=role2)
        self._build_simple_menu(superuser=True)

        url = reverse('creme_config__delete_menu')
        self.assertGET405(url)

        # ---
        self.assertPOST200(url, data={'role': 'superuser'})
        self.assertFalse(MenuConfigItem.objects.filter(superuser=True))
        self.assertEqual(15, MenuConfigItem.objects.count())

        # ---
        self.assertPOST200(url, data={'role': role1.id})
        self.assertFalse(MenuConfigItem.objects.filter(role=role1))
        self.assertEqual(10, MenuConfigItem.objects.count())

        # ---
        self.assertPOST404(url, data={'role': 'not_an_int'})
        self.assertPOST404(url, data={})
