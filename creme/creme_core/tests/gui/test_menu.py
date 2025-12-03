from datetime import timedelta
from functools import partial

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.forms.menu import MenuEntryForm
from creme.creme_core.gui import quick_forms
# from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.gui.menu import (
    ContainerEntry,
    CreationEntry,
    CreationMenuRegistry,
    CustomURLEntry,
    FixedURLEntry,
    ListviewEntry,
    MenuEntry,
    MenuEntrySequence,
    MenuRegistry,
    Separator0Entry,
    Separator1Entry,
    creation_menu_registry,
    menu_registry,
)
from creme.creme_core.menu import (  # RecentEntitiesEntry,
    CremeEntry,
    EntitiesCreationEntry,
    HomeEntry,
    JobsEntry,
    LogoutEntry,
    MyJobsEntry,
    MyPageEntry,
    QuickAccessEntry,
    QuickFormsEntries,
    RoleSwitchEntry,
    TrashEntry,
)
from creme.creme_core.models import (
    CremeEntity,
    CustomEntityType,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    LastViewedEntity,
    MenuConfigItem,
    PinnedEntity,
)

from .. import fake_forms
from ..base import CremeTestCase
from ..fake_menu import FakeContactCreationEntry, FakeContactsEntry


class MenuTestCase(CremeTestCase):
    def _build_context(self, user=None):
        user = user or self.get_root_user()

        return {
            'request': self.build_request(user=user),
            'user': user,
            # 'THEME_NAME': 'icecream',
            'TIME_ZONE': 'Europe/Paris',
        }

    def test_entry(self):
        self.assertEqual('Add an entry', MenuEntry.creation_label)
        self.assertIs(MenuEntry.single_instance, False)
        self.assertIs(MenuEntry.accepts_children, False)

        entry_label = 'Do stuff'

        # ---
        validate = MenuEntry.validate
        expected = {'label': entry_label}
        self.assertDictEqual(expected, validate(data={'label': entry_label}))
        self.assertDictEqual(expected, validate({'label': entry_label, 'foo': 'bar'}))

        # ---
        with self.assertRaises(ValidationError) as cm1:
            validate({'label': ''})

        self.assertValidationError(
            cm1.exception,
            messages='{} -> {}'.format(_('Label'), _('This field is required.')),
        )

        # ---
        with self.assertRaises(ValidationError) as cm2:
            validate({'label': 'foobar' * 10})

        self.assertValidationError(
            cm2.exception,
            messages='{} -> {}'.format(
                _('Label'),
                MaxLengthValidator.message % {
                    'limit_value': 50,
                    'show_value': 60,
                },
            ),
        )

        # ---
        entry0 = MenuEntry()
        self.assertEqual('', entry0.id)
        self.assertEqual('', entry0.label)
        self.assertEqual(1, entry0.level)
        self.assertIs(entry0.is_required, False)
        self.assertIsNone(entry0.config_item_id)
        self.assertDictEqual({}, entry0.data)
        self.assertListEqual([], [*entry0.children])

        with self.assertRaises(AttributeError):
            entry0.children = [MenuEntry(), MenuEntry()]  # NOQA

        ctxt = self._build_context()
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry"></span>',
            entry0.render(ctxt),
        )

        # ---
        entry_id = 'creme_core-my_entry'

        class MyEntry01(MenuEntry):
            id = entry_id
            label = entry_label

        entry1 = MyEntry01()
        self.assertEqual(entry_id,    entry1.id)
        self.assertEqual(entry_label, entry1.label)

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry">{entry_label}</span>',
            entry1.render(ctxt),
        )

        # ---
        class MyEntry02(MenuEntry):
            id = entry_id

        entry2 = MyEntry02(data={'label': entry_label})
        self.assertEqual(entry_id,    entry2.id)
        self.assertEqual(entry_label, entry2.label)

    def test_validate_data(self):
        global_msg = 'Cannot be greater than 40'

        class TestEntryForm(MenuEntryForm):
            count = forms.IntegerField(label='Count')

            def clean(this):
                cdata = super().clean()

                if not this._errors:
                    if cdata['count'] > 40:
                        raise ValidationError(global_msg)

                return cdata

        class TestEntry(MenuEntry):
            form_class = TestEntryForm

            def __init__(this, data=None, **kwargs):
                super().__init__(**kwargs)
                this.count = 0 if not data else data.get('count', 0)

        validate = TestEntry.validate

        with self.assertRaises(ValidationError) as cm1:
            validate(data={'label': 'foobar'})

        self.assertValidationError(
            cm1.exception,
            messages='{} -> {}'.format('Count', _('This field is required.')),
        )

        # ---
        with self.assertRaises(ValidationError) as cm2:
            validate(data={'label': 'foobar', 'count': 'foo'})

        self.assertValidationError(
            cm2.exception,
            messages='{} -> {}'.format('Count', _('Enter a whole number.')),
        )

        # ---
        with self.assertRaises(ValidationError) as cm3:
            validate({'label': 'foobar', 'count': 42})

        self.assertValidationError(cm3.exception, messages=global_msg)

    def test_url_entry(self):
        user = self.login_as_standard()
        self.assertIs(FixedURLEntry.single_instance, True)

        entry_label = 'Home'
        entry_url_name = 'creme_core__home'

        # ---
        validate = FixedURLEntry.validate
        self.assertDictEqual({}, validate(data={'label': ''}))
        self.assertDictEqual({}, validate({'label': entry_label, 'foo': 'bar'}))

        # ---
        class TestEntry(FixedURLEntry):
            id = 'creme_core-test'
            label = entry_label
            url_name = entry_url_name

        self.assertHTMLEqual(
            f'<a href="{reverse(entry_url_name)}">{entry_label}</a>',
            TestEntry().render(self._build_context(user=user)),
        )

    def test_url_entry__standard_user(self):
        "With permissions OK."
        user = self.login_as_standard(admin_4_apps=['creme_config'])

        entry_label = 'Home'
        entry_url_name = 'creme_core__home'

        class TestEntry01(FixedURLEntry):
            id = 'creme_core-test'
            label = entry_label
            url_name = entry_url_name
            permissions = 'creme_core'

        expected = f'<a href="{reverse(entry_url_name)}">{entry_label}</a>'
        ctxt = self._build_context(user=user)
        self.assertHTMLEqual(expected, TestEntry01().render(ctxt))

        # ----
        class TestEntry02(TestEntry01):
            permissions = ('creme_core', 'creme_config.can_admin')

        self.assertHTMLEqual(expected, TestEntry02().render(ctxt))

    def test_url_entry__not_allowed(self):
        user = self.login_as_standard()

        entry_label = 'Home'

        class TestEntry01(FixedURLEntry):
            id = 'creme_core-test'
            label = entry_label
            url_name = 'creme_core__home'
            permissions = 'creme_config'  # <===

        expected = (
            '<span class="ui-creme-navigation-text-entry forbidden" title="{error}">'
            '{label}'
            '</span>'.format(
                label=entry_label,
                error=_('You are not allowed to access to the app: {}').format(
                    _('General configuration')
                ),
            )
        )
        ctxt = self._build_context(user=user)
        self.assertHTMLEqual(expected, TestEntry01().render(ctxt))

        # ----
        class TestEntry02(TestEntry01):
            permissions = ('creme_core', 'creme_config')

        self.assertHTMLEqual(expected, TestEntry02().render(ctxt))

    def test_creation_entry(self):
        self.assertIs(CreationEntry.single_instance, True)

        entry01 = CreationEntry()
        self.assertEqual(_('Create an entity'), entry01.label)

        with self.assertRaises(ValueError):
            entry01.url  # NOQA

        ctxt = self._build_context()
        with self.assertRaises(ValueError):
            entry01.render(ctxt)

        # ---
        entry02 = FakeContactCreationEntry()
        entry_label = _('Create a contact')
        self.assertEqual(entry_label, entry02.label)

        entry_url = reverse('creme_core__create_fake_contact')
        self.assertEqual(entry_url, entry02.url)

        self.assertHTMLEqual(
            f'<a href="{entry_url}">{entry_label}</a>',
            entry02.render(ctxt),
        )

        # ---
        entry03 = FakeContactCreationEntry()  # No item
        self.assertEqual(entry_label, entry03.label)

    def test_creation_entry__standard_user(self):
        "Not super-user, but allowed."
        user = self.login_as_standard(creatable_models=[FakeContact])
        self.assertHTMLEqual(
            f'<a href="{reverse("creme_core__create_fake_contact")}">'
            f'{_("Create a contact")}'
            f'</a>',
            FakeContactCreationEntry().render(self._build_context(user=user)),
        )

    def test_creation_entry__not_allowed(self):
        user = self.login_as_standard()  # creatable_models=[FakeContact]

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{error}">'
            '{label}'
            '</span>'.format(
                label=_('Create a contact'),
                error=_('You are not allowed to create: {}').format('Test Contact'),
            ),
            FakeContactCreationEntry().render(self._build_context(user=user)),
        )

    def test_listview_entry(self):
        self.assertIs(ListviewEntry.single_instance, True)

        ctxt = self._build_context()

        entry01 = ListviewEntry()
        self.assertEqual('Entities', entry01.label)

        with self.assertRaises(ValueError):
            entry01.url  # NOQA

        with self.assertRaises(ValueError):
            entry01.render(ctxt)

        # ----
        entry02 = FakeContactsEntry()
        entry_label = 'Test Contacts'
        self.assertEqual(entry_label, entry02.label)

        entry_url = reverse('creme_core__list_fake_contacts')
        self.assertEqual(entry_url, entry02.url)

        self.assertHTMLEqual(
            f'<a href="{entry_url}">{entry_label}</a>',
            entry02.render(ctxt),
        )

    def test_listview_entry__standard_user(self):
        "Not super-user, but allowed."
        user = self.login_as_standard(listable_models=[FakeContact])

        self.assertHTMLEqual(
            f'<a href="{reverse("creme_core__list_fake_contacts")}">Test Contacts</a>',
            FakeContactsEntry().render(self._build_context(user=user)),
        )

    def test_listview_entry__not_allowed(self):
        user = self.login_as_standard(allowed_apps=['creme_config'])
        self.assertFalse(user.has_perm_to_list(FakeContact))

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden" title="{}">'
            'Test Contacts'
            '</span>'.format(
                # _('You are not allowed to access to the app: {}').format(_('Core')),
                _('You are not allowed to list: {}').format('Test Contact')
            ),
            FakeContactsEntry().render(self._build_context(user=user)),
        )

    def test_container_entry(self):
        self.assertIs(ContainerEntry.single_instance, False)
        self.assertIs(ContainerEntry.accepts_children, True)

        label = 'Main'

        # ---
        validate = ContainerEntry.validate
        self.assertDictEqual({'label': ''},    validate({}))
        self.assertDictEqual({'label': ''},    validate({'label': ''}))
        self.assertDictEqual({'label': label}, validate({'label': label, 'foo': 'bar'}))

        with self.assertRaises(ValidationError) as cm:
            validate({'label': 'foobar' * 10})
        self.assertValidationError(
            cm.exception,
            messages='{} -> {}'.format(
                _('Label'),
                MaxLengthValidator.message % {'limit_value': 50, 'show_value': 60},
            ),
        )

        # ---
        ctxt = self._build_context()

        entry01 = ContainerEntry(data={'label': label})
        self.assertEqual('creme_core-container', entry01.id)
        self.assertEqual(label, entry01.label)
        self.assertFalse(entry01.is_required)
        self.assertListEqual([], [*entry01.children])

        render = entry01.render(ctxt)
        self.assertStartsWith(render, label)
        self.assertHTMLEqual('<ul></ul>', render.removeprefix(label))

        # ----
        children = [FakeContactsEntry(), FakeContactCreationEntry()]

        entry02 = ContainerEntry(data={'label': label})
        entry02.children = children
        self.assertListEqual(children, [*entry02.children])

        self.assertHTMLEqual(
            f'<ul>'
            f'  <li class="ui-creme-navigation-item-id_{FakeContactsEntry.id} '
            f'ui-creme-navigation-item-level1">'
            f'    <a href="{reverse("creme_core__list_fake_contacts")}">Test Contacts</a>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_{FakeContactCreationEntry.id} '
            f'ui-creme-navigation-item-level1">'
            f'    <a href="{reverse("creme_core__create_fake_contact")}">'
            f'      {escape(_("Create a contact"))}'
            f'    </a>'
            f'  </li>'
            f'</ul>',
            entry02.render(ctxt).removeprefix(label),
        )

    def test_container_entry__sequence(self):
        "MenuEntrySequence."
        class SubEntry1(MenuEntry):
            id = 'creme_core-test1'
            label = 'Foo'

        class SubEntry2(MenuEntry):
            id = 'creme_core-test2'
            type = 'creme_core-test'
            label = 'Bar'

        class MyEntrySequence(MenuEntrySequence):
            def __iter__(this):
                yield SubEntry1()
                yield SubEntry2()

        seq_label = 'Interesting entries'
        sequence = MyEntrySequence(data={'label': seq_label})
        self.assertEqual(seq_label, sequence.label)

        ctxt = self._build_context()
        with self.assertRaises(TypeError):
            sequence.render(ctxt)

        label = 'Misc'
        container = ContainerEntry(data={'label': label})
        container.children = [sequence]
        self.assertEqual([sequence], [*container.children])
        self.assertHTMLEqual(
            f'<ul>'
            f'  <li class="ui-creme-navigation-item-id_{SubEntry1.id} '
            f'ui-creme-navigation-item-level1">'
            f'    <span class="ui-creme-navigation-text-entry">{SubEntry1.label}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_{SubEntry2.id} '
            f'ui-creme-navigation-item-type_{SubEntry2.type} '
            f'ui-creme-navigation-item-level1">'
            f'    <span class="ui-creme-navigation-text-entry">{SubEntry2.label}</span>'
            f'  </li>'
            f'</ul>',
            container.render(ctxt).removeprefix(label),
        )

    def test_separator0_entry(self):
        self.assertIs(Separator0Entry.single_instance, False)

        entry = Separator0Entry()
        self.assertEqual('creme_core-separator0', entry.id)
        self.assertEqual(_('Separator'),          entry.label)
        self.assertEqual(0,                       entry.level)

        self.assertEqual('', entry.render(self._build_context()))

    def test_separator1_entry__empty_label(self):
        self.assertEqual(_('Add a separator'), Separator1Entry.creation_label)
        self.assertIs(Separator1Entry.single_instance, False)

        entry = Separator1Entry()
        self.assertEqual('creme_core-separator1', entry.id)
        self.assertEqual('creme_core-separator1', entry.type)
        self.assertEqual('', entry.label)
        self.assertEqual(1,  entry.level)

        self.assertEqual('', entry.render(self._build_context()))

    def test_separator1_entry__label(self):
        label = 'My group'
        entry = Separator1Entry(data={'label': label})
        self.assertEqual(label, entry.label)
        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-title">{label}</span>',
            entry.render(self._build_context()),
        )

    def test_custom_url_entry(self):
        label = 'Python'
        url = 'http://www.python.org'

        self.assertEqual(_('Add a URL entry'), CustomURLEntry.creation_label)
        self.assertIs(CustomURLEntry.single_instance, False)

        # ---
        validate = CustomURLEntry.validate

        with self.assertRaises(ValidationError) as cm1:
            validate(data={'label': label})
        self.assertValidationError(
            cm1.exception,
            messages='{} -> {}'.format(_('URL'), _('This field is required.')),
        )

        with self.assertRaises(ValidationError) as cm2:
            validate({'label': label, 'url': '1234'})
        self.assertValidationError(
            cm2.exception,
            messages='{} -> {}'.format(_('URL'), _('Enter a valid URL.')),
        )

        with self.assertRaises(ValidationError) as cm3:
            validate({'label': '', 'url': url})
        self.assertValidationError(
            cm3.exception,
            messages='{} -> {}'.format(_('Label'), _('This field is required.')),
        )

        self.assertDictEqual(
            {'label': label, 'url': url},
            validate({'label': label, 'url': url, 'foo': 'bar'}),
        )

        # ---
        entry = CustomURLEntry(data={'label': label, 'url': url})
        self.assertEqual(label, entry.label)
        self.assertEqual(url, entry.url)
        self.assertDictEqual({'label': label, 'url': url}, entry.data)
        self.assertHTMLEqual(
            f'<a href="{url}" target="_blank">{label}</a>',
            entry.render(self._build_context()),
        )

    def test_custom_url_entry__no_data(self):
        "No data."
        label = 'Python'
        entry = CustomURLEntry(data={'label': label})
        self.assertEqual(label, entry.label)
        self.assertEqual('', entry.url)
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">{}</span>'.format(
                _('{label} (broken configuration)').format(label=label),
            ),
            entry.render(self._build_context()),
        )

    def test_custom_url_entry__no_url(self):
        label = 'Python'
        entry = CustomURLEntry(data={'label': label, 'foo': 'bar'})
        self.assertEqual(label, entry.label)
        self.assertEqual('', entry.url)

    def test_home_entry(self):
        self.assertTrue(HomeEntry.single_instance)

        entry = HomeEntry()

        entry_id = 'creme_core-home'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Home')
        self.assertEqual(entry_label, entry.label)

        entry_url = reverse('creme_core__home')
        self.assertEqual(entry_url, entry.url)

        self.assertHTMLEqual(
            f'<a href="{entry_url}">{entry_label}</a>',
            entry.render(self._build_context()),
        )

    def test_jobs_entry(self):
        self.assertTrue(JobsEntry.single_instance)

        entry = JobsEntry()

        entry_id = 'creme_core-jobs'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Jobs')
        self.assertEqual(entry_label, entry.label)

        entry_url = reverse('creme_core__jobs')
        self.assertEqual(entry_url, entry.url)

        self.assertHTMLEqual(
            f'<a href="{entry_url}">{entry_label}</a>',
            entry.render(self._build_context()),
        )

    def test_trash_entry(self):
        user = self.get_root_user()
        self.assertTrue(TrashEntry.single_instance)

        entry = TrashEntry()

        entry_id = 'creme_core-trash'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Trash')
        self.assertEqual(entry_label, entry.label)

        entry_url = reverse('creme_core__trash')
        self.assertEqual(entry_url, entry.url)

        FakeOrganisation.objects.create(user=user, name='Acme', is_deleted=True)
        count = CremeEntity.objects.filter(is_deleted=True).count()
        count_label = ngettext(
            '{count} entity',
            '{count} entities',
            count,
        ).format(count=count)
        self.assertHTMLEqual(
            f'<a href="{entry_url}">'
            f'{entry_label} '
            f'<span class="ui-creme-navigation-punctuation">(</span>'
            f'{count_label}'
            f'<span class="ui-creme-navigation-punctuation">)</span>'
            f'</a>',
            entry.render(self._build_context(user=user)),
        )

    def test_role_switch_entry(self):
        entry = RoleSwitchEntry()

        entry_id = 'creme_core-role_switch'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Available roles')
        self.assertEqual(entry_label, entry.label)

        # Superuser ---
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-title ui-creme-navigation-empty" />',
            entry.render(self._build_context(user=self.get_root_user())),
        )

        # One role ---
        role1 = self.create_role(name='CEO')
        user = self.create_user(role=role1, roles=[role1])
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-title ui-creme-navigation-empty" />',
            entry.render(self._build_context(user=user)),
        )

        # Several roles ---
        role2 = self.create_role(name='Engineer')
        role3 = self.create_role(name='Project leader', deactivated_on=now())
        user.roles.add(role2, role3)
        self.maxDiff = None
        self.assertHTMLEqual(
            '''
<span class="ui-creme-navigation-title">{label}</span>
<button class="" disabled onclick="creme.utils.ajaxQuery('{url1}', {{action: 'post'}}).onDone(function(){{ creme.utils.goTo('{home_url}'); }}).start()">
 <div class="marker-selected" />{role_label1}
</button>
<button class="" onclick="creme.utils.ajaxQuery('{url2}', {{action: 'post'}}).onDone(function(){{ creme.utils.goTo('{home_url}'); }}).start()">
 <div class="marker-not-selected" />{role_label2}
</button>
<button class="disabled-role" disabled onclick="creme.utils.ajaxQuery('{url3}', {{action: 'post'}}).onDone(function(){{ creme.utils.goTo('{home_url}'); }}).start()">
 <div class="marker-not-selected" />{role_label3}
</button>
            '''.format(   # NOQA
                label=_('Available roles'),

                role_label1=role1.name,
                url1=reverse('creme_core__switch_role', args=(user.id, role1.id)),

                role_label2=role2.name,
                url2=reverse('creme_core__switch_role', args=(user.id, role2.id)),

                role_label3=str(role3),
                url3=reverse('creme_core__switch_role', args=(user.id, role3.id)),

                home_url=reverse('creme_core__home'),
            ),
            entry.render(self._build_context(user=user)),
        )

    def test_logout_entry(self):
        self.assertTrue(LogoutEntry.single_instance)

        entry = LogoutEntry()
        self.assertEqual('creme_core-logout', entry.id)
        self.assertEqual(_('Log out'), entry.label)
        self.assertEqual(reverse('creme_logout'), entry.url)

    @override_settings(SOFTWARE_LABEL='Creme')
    def test_creme_entry(self):
        self.assertTrue(CremeEntry.single_instance)

        label = 'Creme'
        entry = CremeEntry()
        self.assertEqual(label, entry.label)
        self.assertEqual('creme_core-creme', entry.id)
        self.assertEqual(0, entry.level)
        self.assertIs(entry.is_required, True)
        self.assertFalse(entry.accepts_children)

        children = [*entry.children]

        def assertInChildren(entry_cls):
            for child in children:
                if isinstance(child, entry_cls):
                    return

            self.fail(f'No child with class {entry_cls} found in {children}.')

        assertInChildren(HomeEntry)
        assertInChildren(TrashEntry)
        assertInChildren(MyPageEntry)
        assertInChildren(MyJobsEntry)
        assertInChildren(RoleSwitchEntry)
        assertInChildren(LogoutEntry)

        render = entry.render(self._build_context())
        self.assertStartsWith(render, label)

        tree = self.get_html_tree(render.removeprefix(label))
        li_classes = set()
        for li_node in tree.findall('.//li'):
            classes = {*li_node.get('class').split()}
            if 'ui-creme-navigation-item-level1' in classes:
                li_classes |= classes

        self.assertIn('ui-creme-navigation-item-id_creme_core-home', li_classes)
        self.assertIn('ui-creme-navigation-item-id_creme_core-trash', li_classes)

        # ---
        entry.children = [HomeEntry()]  # Should not be set
        self.assertGreater(len([*entry.children]), 1)

    @override_settings(SOFTWARE_LABEL='My amazing CRM')
    def test_creme_entry__other_label(self):
        self.assertEqual('My amazing CRM', CremeEntry().label)

    # def test_recent_entities_entry01(self):
    #     user = self.get_root_user()
    #     self.assertTrue(RecentEntitiesEntry.single_instance)
    #
    #     contact1 = user.linked_contact
    #     contact2 = FakeContact.objects.create(
    #         user=user, first_name='Kirika', last_name='Yumura',
    #     )
    #
    #     ctxt = self._build_context()
    #     request = ctxt['request']
    #     LastViewedItem(request, contact1)
    #     LastViewedItem(request, contact2)
    #
    #     entry = RecentEntitiesEntry()
    #     self.assertEqual(0, entry.level)
    #
    #     entry_id = 'creme_core-recent_entities'
    #     self.assertEqual(entry_id, entry.id)
    #
    #     entry_label = _('Recent entities')
    #     self.assertEqual(entry_label, entry.label)
    #
    #     render = entry.render(ctxt)
    #     self.assertStartsWith(render, entry_label)
    #     self.assertHTMLEqual(
    #         f'<ul>'
    #         f'  <li>'
    #         f'    <a href="{contact2.get_absolute_url()}">'
    #         f'      <span class="ui-creme-navigation-ctype">{contact2.entity_type}</span>'
    #         f'      {contact2}'
    #         f'    </a>'
    #         f'  </li>'
    #         f'  <li>'
    #         f'    <a href="{contact1.get_absolute_url()}">'
    #         f'      <span class="ui-creme-navigation-ctype">{contact1.entity_type}</span>'
    #         f'      {contact1}'
    #         f'    </a>'
    #         f'  </li>'
    #         f'</ul>',
    #         render.removeprefix(entry_label),
    #     )
    #
    # def test_recent_entities_entry02(self):
    #     entry = RecentEntitiesEntry()
    #
    #     entry_label = _('Recent entities')
    #     self.assertEqual(entry_label, entry.label)
    #
    #     render = entry.render(self._build_context())
    #     self.assertStartsWith(render, entry_label)
    #     self.assertHTMLEqual(
    #         '<ul>'
    #         '   <li><span class="ui-creme-navigation-text-entry">{}</span></li>'
    #         '</ul>'.format(escape(_('No recently visited entity'))),
    #         render.removeprefix(entry_label),
    #     )
    def test_quick_access_entry__empty(self):
        entry = QuickAccessEntry()
        self.assertTrue(QuickAccessEntry.single_instance)

        entry_label = _('Quick access')
        self.assertEqual(entry_label, entry.label)

        render = entry.render(self._build_context())
        self.assertStartsWith(render, entry_label)
        # self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Recent entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_ ui-creme-navigation-item-level1">'
            f'   <span class="ui-creme-navigation-text-entry">'
            f'     {escape(_("No recently visited entity"))}'
            f'   </span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Pinned entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_ ui-creme-navigation-item-level1">'
            f'   <span class="ui-creme-navigation-text-entry">'
            f'   {escape(_("No pinned entity"))}'
            f'   </span>'
            f'</ul>',
            render.removeprefix(entry_label),
        )

    @override_settings(LAST_ENTITIES_SIZE=10, LAST_ENTITIES_MENU_SIZE=2)
    def test_quick_access_entry__recent_entities(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')
        contact4 = create_contact(last_name='Moriarty')

        create_last_viewed = partial(LastViewedEntity.objects.create, user=user)
        lve1 = create_last_viewed(real_entity=contact1)
        lve2 = create_last_viewed(real_entity=contact2)
        lve3 = create_last_viewed(real_entity=contact3)
        lve4 = create_last_viewed(real_entity=contact4)
        lve_other = create_last_viewed(real_entity=contact1, user=self.create_user())

        # entity=NULL after a deletion => should be ignored
        LastViewedEntity(user=user, entity_ctype=FakeContact).save()

        def offset_viewed(lve, delta):
            LastViewedEntity.objects.filter(id=lve.id).update(viewed=now() - delta)

        offset_viewed(lve1, delta=timedelta(minutes=10))
        offset_viewed(lve2, delta=timedelta(minutes=8))
        offset_viewed(lve3, delta=timedelta(minutes=5))
        offset_viewed(lve4, delta=timedelta(minutes=3))
        offset_viewed(lve_other, delta=timedelta(minutes=1))

        contact4.trash()

        entry = QuickAccessEntry()
        self.assertEqual(0, entry.level)

        entry_id = 'creme_core-recent_entities'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Quick access')
        render = entry.render(self._build_context())
        self.assertStartsWith(render, entry_label)
        # self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Recent entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-recent_entity-link'
            f'      ui-creme-navigation-item-level1">'
            f'    <a href="{contact3.get_absolute_url()}">'
            f'      <span class="ui-creme-navigation-ctype">{contact3.entity_type}</span>'
            f'      {contact3}'
            f'    </a>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-recent_entity-link'
            f'      ui-creme-navigation-item-level1">'
            f'    <a href="{contact2.get_absolute_url()}">'
            f'      <span class="ui-creme-navigation-ctype">{contact2.entity_type}</span>'
            f'      {contact2}'
            f'    </a>'
            f'  </li>'
            # f'  <li class="...">'
            # f'    <a href="{contact1.get_absolute_url()}">'
            # f'      <span class="ui-creme-navigation-ctype">{contact1.entity_type}</span>'
            # f'      {contact1}'
            # f'    </a>'
            # f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Pinned entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_ ui-creme-navigation-item-level1">'
            f'   <span class="ui-creme-navigation-text-entry">'
            f'   {escape(_("No pinned entity"))}'
            f'   </span>'
            f'  </li>'
            f'</ul>',
            render.removeprefix(entry_label),
        )

    @override_settings(PINNED_ENTITIES_SIZE=3)
    def test_quick_access_entry__pinned_entities(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        create_contact = partial(FakeContact.objects.create, user=user1)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson', is_deleted=True)
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        create_pinned = PinnedEntity.objects.create
        create_pinned(real_entity=contact1, user=user1)
        create_pinned(real_entity=contact2, user=user1)
        create_pinned(real_entity=contact3, user=user2)

        entry_label = _('Quick access')

        render = QuickAccessEntry().render(self._build_context())
        self.assertStartsWith(render, entry_label)
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Recent entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_ ui-creme-navigation-item-level1">'
            f'   <span class="ui-creme-navigation-text-entry">'
            f'     {escape(_("No recently visited entity"))}'
            f'   </span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-separator1'
            f'      ui-creme-navigation-item-level1'
            f'      ui-creme-navigation-item-type_creme_core-separator1">'
            f'   <span class="ui-creme-navigation-title">{escape(_("Pinned entities"))}</span>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-pinned_entity-link'
            f'      ui-creme-navigation-item-level1">'
            f'    <a href="{contact1.get_absolute_url()}" class="">'
            f'      <span class="ui-creme-navigation-ctype">{contact1.entity_type}</span>'
            f'      {contact1}'
            f'    </a>'
            f'  </li>'
            f'  <li class="ui-creme-navigation-item-id_creme_core-pinned_entity-link'
            f'      ui-creme-navigation-item-level1">'
            f'    <a href="{contact2.get_absolute_url()}" class="is_deleted">'
            f'      <span class="ui-creme-navigation-ctype">{contact2.entity_type}</span>'
            f'      {contact2}'
            f'    </a>'
            f'  </li>'
            f'</ul>',
            render.removeprefix(entry_label),
        )

    def test_quick_forms_entries(self):
        user = self.login_as_standard()

        seq = QuickFormsEntries()
        self.assertIsInstance(seq, MenuEntrySequence)
        self.assertEqual('creme_core-quick_forms', seq.id)
        self.assertEqual(_('*Quick forms*'),       seq.label)
        self.assertEqual(1,                        seq.level)
        self.assertFalse(seq.single_instance)
        self.assertIs(quick_forms.quickform_registry, seq.quickforms_registry)

        with self.assertNoException():
            cdata = QuickFormsEntries.validate({})
        self.assertDictEqual({}, cdata)

        registry = quick_forms.QuickFormRegistry()
        seq.quickforms_registry = registry

        entry11 = self.get_alone_element(seq)
        self.assertIsInstance(entry11, MenuEntry)
        self.assertEqual(_('No type available'), entry11.label)

        # ---
        registry.register(
            FakeOrganisation, fake_forms.FakeOrganisationQuickForm,
        ).register(
            FakeContact,      fake_forms.FakeContactQuickForm,
        )

        entries2 = [*seq]
        self.assertEqual(2, len(entries2))

        entry21 = entries2[0]
        self.assertIsInstance(entry21, QuickFormsEntries.QuickCreationEntry)
        label1 = 'Test Contact'
        self.assertEqual(label1,                        entry21.label)
        self.assertEqual(FakeContact,                   entry21.model)
        self.assertEqual('creme_core-quick_forms-link', entry21.id)

        contact_ctype = ContentType.objects.get_for_model(FakeContact)
        url1 = reverse('creme_core__quick_form', args=(contact_ctype.id,))
        self.assertEqual(url1, entry21.url)

        self.assertFalse(user.has_perm_to_create(FakeContact))
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">Test Contact</span>',
            entry21.render(self._build_context(user=user)),
        )

        user.role.creatable_ctypes.set([contact_ctype])
        user = self.refresh(user)
        self.assertTrue(user.has_perm_to_create(FakeContact))
        self.assertHTMLEqual(
            f'<a href="#" data-href="{url1}" class="quickform-menu-link">{label1}</a>',
            entry21.render(self._build_context(user=user)),
        )

        self.assertEqual(FakeOrganisation, entries2[1].model)

    def test_creation_forms_entry(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()
        self.assertEqual('creme_core-creation_forms', entry.id)
        self.assertEqual(_('Other type of entity'),   entry.label)
        self.assertEqual(1,                           entry.level)
        self.assertIs(creation_menu_registry, entry.creation_menu_registry)

        with self.assertNoException():
            cdata = EntitiesCreationEntry.validate({})
        self.assertDictEqual({}, cdata)

        registry = CreationMenuRegistry()
        self.assertEqual([], [*registry])
        self.assertEqual('CreationMenuRegistry:\n', registry.verbose_str)

        entry.creation_menu_registry = registry

        registry.get_or_create_group(
            group_id='persons', label='Directory',
        ).add_link(
            'add_contact', label='Contact', url='/tests/contact/add',
            perm='creme_core.add_fakecontact',
        )
        self.assertEqual(1, len([*registry]))
        self.assertEqual(
            'CreationMenuRegistry:\n'
            '  <Group: id="persons" label="Directory" priority=1>\n'
            '    <Link: id="add_contact" label="Contact" priority=1>\n',
            registry.verbose_str,
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [{'label': 'Contact', 'url': '/tests/contact/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'persons', 'Directory',
        ).add_link(
            'add_orga', label='Organisation', url='/tests/organisation/add',
            perm='creme_core.add_fakeorganisation',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    },
                ]
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'activities', 'Activities',
        ).add_link(
            'add_pcall', label='Phone call', url='/tests/phone_call/add',
            perm='creme_core.add_fakeactivity',
        ).add_link(
            'add_meeting', label='Meeting', url='/tests/meeting/add',
            perm='creme_core.add_fakeactivity',
        )
        registry.get_or_create_group(
            'tools', 'Tools',
        ).add_link(
            'add_doc', label='Document', url='/tests/document/add',
            perm='creme_core.add_fakedocument',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    },
                ], [
                    {
                        'label': 'Activities',
                        'links': [
                            {'label': 'Phone call', 'url': '/tests/phone_call/add'},
                            {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
                    }, {
                        'label': 'Tools',
                        'links': [{'label': 'Document', 'url': '/tests/document/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'analysis', 'Analysis',
        ).add_link(
            'add_report', label='Report', url='/tests/report/add',
            perm='creme_core.add_fakereport',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    }, {
                        'label': 'Activities',
                        'links': [
                            {'label': 'Phone call', 'url': '/tests/phone_call/add'},
                            {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
                    },
                ], [
                    {
                        'label': 'Tools',
                        'links': [{'label': 'Document', 'url': '/tests/document/add'}],
                    }, {
                        'label': 'Analysis',
                        'links': [{'label': 'Report', 'url': '/tests/report/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'management', 'Management',
        ).add_link(
            'add_invoice', label='Invoice', url='/tests/invoice/add',
            perm='creme_core.add_fakeinvoice',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    },
                ], [
                    {
                        'label': 'Activities',
                        'links': [
                            {'label': 'Phone call', 'url': '/tests/phone_call/add'},
                            {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
                    }, {
                        'label': 'Tools',
                        'links': [{'label': 'Document', 'url': '/tests/document/add'}],
                    },
                ], [
                    {
                        'label': 'Analysis',
                        'links': [{'label': 'Report', 'url': '/tests/report/add'}],
                    }, {
                        'label': 'Management',
                        'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
                    },
                ]
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'commercial', 'Commercial',
        ).add_link(
            'add_act', label='Act', url='/tests/act/add', perm='creme_core',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    }, {
                        'label': 'Activities',
                        'links': [
                            {'label': 'Phone call', 'url': '/tests/phone_call/add'},
                            {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
                    },
                ], [
                    {
                        'label': 'Tools',
                        'links': [{'label': 'Document', 'url': '/tests/document/add'}],
                    }, {
                        'label': 'Analysis',
                        'links': [{'label': 'Report', 'url': '/tests/report/add'}],
                    },
                ], [
                    {
                        'label': 'Management',
                        'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
                    }, {
                        'label': 'Commercial',
                        'links': [{'label': 'Act', 'url': '/tests/act/add'}],
                    },
                ]
            ],
            entry.as_grid(user),
        )

        registry.get_or_create_group(
            'marketing', 'Marketing',
        ).add_link(
            'add_campaign', label='Campaign', url='/tests/campaign/add', perm='creme_core',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Contact',      'url': '/tests/contact/add'},
                            {'label': 'Organisation', 'url': '/tests/organisation/add'},
                        ],
                    }, {
                        'label': 'Activities',
                        'links': [
                            {'label': 'Phone call', 'url': '/tests/phone_call/add'},
                            {'label': 'Meeting',    'url': '/tests/meeting/add'},
                        ],
                    },
                ], [
                    {
                        'label': 'Tools',
                        'links': [{'label': 'Document', 'url': '/tests/document/add'}],
                    }, {
                        'label': 'Analysis',
                        'links': [{'label': 'Report', 'url': '/tests/report/add'}],
                    },
                ], [
                    {
                        'label': 'Management',
                        'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
                    }, {
                        'label': 'Commercial',
                        'links': [{'label': 'Act', 'url': '/tests/act/add'}],
                    }, {
                        'label': 'Marketing',
                        'links': [{'label': 'Campaign', 'url': '/tests/campaign/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

    def test_creation_forms_entry__simplified_api(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()

        registry1 = CreationMenuRegistry()

        registry1.get_or_create_group(
            'persons', 'Directory',
        ).add_link('add_contact', FakeContact)
        entry.creation_menu_registry = registry1
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        # ----
        registry2 = CreationMenuRegistry()

        label = 'Contact'
        url = '/tests/customer/add'
        registry2.get_or_create_group(
            'persons', 'Directory',
        ).add_link('add_contact', FakeContact, label=label, url=url)

        entry.creation_menu_registry = registry2
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [{'label': label, 'url': url}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        # ----
        group = CreationMenuRegistry().get_or_create_group('persons', 'Directory')

        with self.assertRaises(TypeError):
            group.add_link('add_contact', label=label, url=url)  # No model + missing perm

    def test_creation_forms_entry__link_priority(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()
        registry = entry.creation_menu_registry = CreationMenuRegistry()
        group = registry.get_or_create_group('persons', 'Directory')

        group.add_link(
            'add_contact', FakeContact,      priority=10,
        ).add_link(
            'add_orga',    FakeOrganisation, priority=5,
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                            {'label': 'Test Contact',      'url': '/tests/contact/add'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        group.add_link(
            'add_customer', label='Customer', url='/tests/customer/add',
            perm='creme_core.add_fakecontact',
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                            {'label': 'Test Contact',      'url': '/tests/contact/add'},
                            {'label': 'Customer',          'url': '/tests/customer/add'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        group.add_link(
            'add_propect', label='Prospect', url='/tests/prospect/add',
            perm='creme_core.add_fakecontact', priority=15,
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                            {'label': 'Test Contact',      'url': '/tests/contact/add'},
                            {'label': 'Customer',          'url': '/tests/customer/add'},
                            {'label': 'Prospect',          'url': '/tests/prospect/add'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        group.change_links_priority(1, 'add_propect', 'add_customer')
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Prospect',          'url': '/tests/prospect/add'},
                            {'label': 'Customer',          'url': '/tests/customer/add'},
                            {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                            {'label': 'Test Contact',      'url': '/tests/contact/add'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        with self.assertRaises(KeyError):
            group.change_links_priority(2, 'add_customer', 'unknown')

    def test_creation_forms_entry__remove_link(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()
        registry = entry.creation_menu_registry = CreationMenuRegistry()
        group = registry.get_or_create_group('persons', 'Directory')

        group.add_link(
            'add_contact', FakeContact,
        ).add_link(
            'add_orga', FakeOrganisation,
        ).add_link(
            'add_prospect', label='Prospect', url='/tests/propect/add',
            perm='creme_core.add_fakecontact',
        )

        group.remove_links('add_contact', 'add_prospect', 'invalid')
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

    def test_creation_forms_entry__group_priority(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()
        registry = entry.creation_menu_registry = CreationMenuRegistry()

        registry.get_or_create_group(
            'persons', 'Directory', priority=10,
        ).add_link('add_contact', FakeContact)
        registry.get_or_create_group(
            'tools', 'Tools', priority=2,
        ).add_link('add_doc', FakeDocument)

        self.assertListEqual(
            [
                [
                    {
                        'label': 'Tools',
                        'links': [{'label': 'Test Document', 'url': ''}],
                    },
                ], [
                    {
                        'label': 'Directory',
                        'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

        registry.change_groups_priority(1, 'persons')
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
                    },
                ], [
                    {
                        'label': 'Tools',
                        'links': [{'label': 'Test Document', 'url': ''}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

    def test_creation_forms_entry__remove_group(self):
        user = self.get_root_user()
        entry = EntitiesCreationEntry()
        registry = entry.creation_menu_registry = CreationMenuRegistry()

        registry.get_or_create_group('tools', 'Tools').add_link('add_doc', FakeDocument)
        registry.get_or_create_group('persons', 'Directory').add_link('add_contact', FakeContact)
        registry.get_or_create_group('activities', 'Activities').add_link('add_act', FakeActivity)

        registry.remove_groups('tools', 'activities', 'unknown')
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
                    },
                ],
            ],
            entry.as_grid(user),
        )

    def test_creation_forms_entry__credentials(self):
        user = self.login_as_standard(creatable_models=[FakeContact])
        entry = EntitiesCreationEntry()
        registry = entry.creation_menu_registry = CreationMenuRegistry()

        registry.get_or_create_group(
            'persons', 'Directory',
        ).add_link(
            'add_contact', FakeContact,
        ).add_link(
            'add_orga', FakeOrganisation,
        )
        self.assertListEqual(
            [
                [
                    {
                        'label': 'Directory',
                        'links': [
                            {'label': 'Test Contact', 'url': '/tests/contact/add'},
                            {'label': 'Test Organisation'},
                        ],
                    },
                ],
            ],
            entry.as_grid(user),
        )

    def test_creation_forms_entry__id_uniqueness(self):
        "ID uniqueness."
        registry = CreationMenuRegistry()

        group = registry.get_or_create_group(
            'persons', 'Directory',
        ).add_link('add_contact', FakeContact)

        with self.assertRaises(ValueError):
            group.add_link('add_contact', FakeContact, label='Contact')

    def test_creation_forms_entry__custom_types(self):
        self.get_root_user()
        registry = CreationMenuRegistry()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.save()

        groups = [*registry]
        self.assertEqual(1, len(groups))

        custom_group = groups[0]
        self.assertEqual('custom_entities',    custom_group.id)
        self.assertEqual(_('Custom entities'), custom_group.label)

        links = [*custom_group]
        self.assertEqual(1, len(links))

        link = links[0]
        self.assertEqual('creme_core-create_custom1', link.id)
        self.assertEqual(ce_type.entity_model,        link.model)
        self.assertEqual(ce_type.name,                link.label)

    def test_registry01(self):
        item1 = MenuConfigItem(id=1, entry_id=CremeEntry.id, order=0)
        items = [item1]

        registry = MenuRegistry()
        self.assertListEqual([], registry.get_entries(items))
        self.assertListEqual([], [*registry.entry_classes])
        self.assertIsNone(registry.get_class(CremeEntry.id))

        # -------------
        registry.register(FakeContactsEntry, CremeEntry)
        self.assertCountEqual([FakeContactsEntry, CremeEntry], registry.entry_classes)

        entries = registry.get_entries(items)
        self.assertIsList(entries, length=1)

        entry1 = entries[0]
        self.assertIsInstance(entry1, CremeEntry)
        self.assertEqual(item1.id, entry1.config_item_id)

        self.assertEqual(CremeEntry,        registry.get_class(CremeEntry.id))
        self.assertEqual(FakeContactsEntry, registry.get_class(FakeContactsEntry.id))

        # Empty ID ---
        class EmptyID(MenuEntry):
            # id = FakeContactsEntry.id
            pass

        with self.assertRaises(MenuRegistry.RegistrationError):
            registry.register(EmptyID)

        # Duplicate ---
        class Duplicate(MenuEntry):
            id = FakeContactsEntry.id

        with self.assertRaises(MenuRegistry.RegistrationError):
            registry.register(Duplicate)

        # Invalid ID ---
        class InvalidID(MenuEntry):
            id = 'foo"<bar>"'

        with self.assertRaises(MenuRegistry.RegistrationError):
            registry.register(InvalidID)

    def test_registry__container_with_children(self):
        container_name = 'Contact'
        container_item = MenuConfigItem(
            id=1, entry_id=ContainerEntry.id,
            entry_data={'label': container_name},
        )

        url_name = 'Mastodon'
        url = 'http://mastodon.mycompagny.com'

        sub_items = [
            MenuConfigItem(
                id=2, entry_id=FakeContactsEntry.id, parent_id=container_item.id
            ),
            MenuConfigItem(
                id=3, entry_id=FakeContactCreationEntry.id, parent_id=container_item.id
            ),
            MenuConfigItem(
                id=4, entry_id=CustomURLEntry.id, parent_id=container_item.id,
                entry_data={'label': url_name, 'url': url},
            ),
        ]

        registry = MenuRegistry().register(
            ContainerEntry, CustomURLEntry,
            FakeContactsEntry, FakeContactCreationEntry,
        )
        self.assertListEqual([], registry.get_entries(sub_items))

        # -------------
        registry.register(FakeContactsEntry, CremeEntry)
        entries = registry.get_entries([container_item, *sub_items])
        self.assertIsList(entries, length=1)

        entry = entries[0]
        self.assertIsInstance(entry, ContainerEntry)
        self.assertEqual(container_name, entry.label)
        self.assertEqual(1,              entry.config_item_id)

        children = [*entry.children]
        self.assertEqual(3, len(children))

        children1 = children[0]
        self.assertIsInstance(children1, FakeContactsEntry)
        self.assertEqual(2,              children1.config_item_id)

        self.assertIsInstance(children[1], FakeContactCreationEntry)

        children3 = children[2]
        self.assertIsInstance(children3, CustomURLEntry)
        self.assertEqual(url_name, children3.label)
        self.assertEqual(url,      children3.url)
        self.assertEqual(4,        children3.config_item_id)

    def test_registry__container_without_children(self):
        "Container does not accept children."
        # container_item = MenuConfigItem(id=1, entry_id=RecentEntitiesEntry.id)
        container_item = MenuConfigItem(id=1, entry_id=QuickAccessEntry.id)
        sub_item = MenuConfigItem(
            id=2, entry_id=FakeContactsEntry.id, parent_id=container_item.id,
        )
        # registry = MenuRegistry().register(RecentEntitiesEntry, FakeContactsEntry)
        registry = MenuRegistry().register(QuickAccessEntry, FakeContactsEntry)

        entry = self.get_alone_element(
            registry.get_entries([container_item, sub_item])
        )
        # self.assertIsInstance(entry, RecentEntitiesEntry)
        self.assertIsInstance(entry, QuickAccessEntry)
        self.assertFalse([*entry.children])

    def test_registry_unregister(self):
        registry = MenuRegistry().register(
            # CremeEntry, RecentEntitiesEntry, FakeContactsEntry,
            CremeEntry, QuickAccessEntry, FakeContactsEntry,
        )

        # registry.unregister(RecentEntitiesEntry, FakeContactsEntry)
        registry.unregister(QuickAccessEntry, FakeContactsEntry)
        entry_classes = {*registry.entry_classes}
        self.assertIn(CremeEntry, entry_classes)
        # self.assertNotIn(RecentEntitiesEntry, entry_classes)
        self.assertNotIn(QuickAccessEntry, entry_classes)
        self.assertNotIn(FakeContactsEntry,   entry_classes)

        # ---
        with self.assertRaises(registry.UnRegistrationError) as cm:
            registry.unregister(CremeEntry, FakeContactsEntry)

        self.assertEqual(
            f'Invalid entry {FakeContactsEntry} (already unregistered?)',
            str(cm.exception),
        )

    def test_global_registry(self):
        entry_classes = {*menu_registry.entry_classes}
        self.assertIn(ContainerEntry,        entry_classes)
        self.assertIn(Separator0Entry,       entry_classes)
        self.assertIn(Separator1Entry,       entry_classes)
        self.assertIn(CustomURLEntry,        entry_classes)
        self.assertIn(CremeEntry,            entry_classes)
        self.assertIn(QuickFormsEntries,     entry_classes)
        self.assertIn(EntitiesCreationEntry, entry_classes)
        # self.assertIn(RecentEntitiesEntry,   entry_classes)
        self.assertIn(QuickAccessEntry,   entry_classes)
