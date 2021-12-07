# -*- coding: utf-8 -*-

# from xml.etree import ElementTree
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
# from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.forms.menu import MenuEntryForm
from creme.creme_core.gui import quick_forms
from creme.creme_core.gui.last_viewed import LastViewedItem
# from creme.creme_core.gui.menu import (
#     ContainerItem,
#     CreationFormsItem,
#     ItemGroup,
#     LabelItem,
#     Menu,
#     URLItem,
#     ViewableItem,
# )
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
from creme.creme_core.menu import (
    CremeEntry,
    EntitiesCreationEntry,
    HomeEntry,
    JobsEntry,
    LogoutEntry,
    MyJobsEntry,
    MyPageEntry,
    QuickFormsEntries,
    RecentEntitiesEntry,
    TrashEntry,
)
from creme.creme_core.models import (
    CremeEntity,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    MenuConfigItem,
)

from .. import fake_forms
from ..base import CremeTestCase
from ..fake_menu import FakeContactCreationEntry, FakeContactsEntry


class MenuTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def build_context(self, user=None):
        user = user or self.user

        return {
            'request': self.build_request(user=user),
            'user': user,
            # 'THEME_NAME': 'icecream',
            'TIME_ZONE': 'Europe/Paris',
        }

    def test_entry(self):
        self.login()
        self.assertEqual('Add an entry', MenuEntry.creation_label)
        self.assertIs(MenuEntry.single_instance, False)
        self.assertIs(MenuEntry.accepts_children, False)

        entry_label = 'Do stuff'

        # ---
        validate = MenuEntry.validate
        expected = {'label': entry_label}
        self.assertDictEqual(expected, validate(data={'label': entry_label}))
        self.assertDictEqual(expected, validate({'label': entry_label, 'foo': 'bar'}))

        with self.assertRaises(ValidationError) as cm1:
            validate({'label': ''})
        self.assertEqual(
            '{} -> {}'.format(_('Label'), _('This field is required.')),
            ','.join(cm1.exception.messages),
        )

        with self.assertRaises(ValidationError) as cm2:
            validate({'label': 'foobar' * 10})
        self.assertEqual(
            '{} -> {}'.format(
                _('Label'),
                MaxLengthValidator.message % {
                    'limit_value': 50,
                    'show_value': 60,
                },
            ),
            ','.join(cm2.exception.messages),
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

        ctxt = self.build_context()
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
        self.assertEqual(
            '{} -> {}'.format('Count', _('This field is required.')),
            ','.join(cm1.exception.messages),
        )

        with self.assertRaises(ValidationError) as cm2:
            validate(data={'label': 'foobar', 'count': 'foo'})
        self.assertEqual(
            '{} -> {}'.format('Count', _('Enter a whole number.')),
            ','.join(cm2.exception.messages),
        )

        with self.assertRaises(ValidationError) as cm3:
            validate({'label': 'foobar', 'count': 42})
        self.assertEqual(
            global_msg, ','.join(cm3.exception.messages),
        )

    def test_url_entry01(self):
        self.login(is_superuser=False)
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
            TestEntry().render(self.build_context()),
        )

    def test_url_entry02(self):
        "With permissions OK."
        self.login(is_superuser=False, admin_4_apps=['creme_config'])

        entry_label = 'Home'
        entry_url_name = 'creme_core__home'

        class TestEntry01(FixedURLEntry):
            id = 'creme_core-test'
            label = entry_label
            url_name = entry_url_name
            permissions = 'creme_core'

        expected = f'<a href="{reverse(entry_url_name)}">{entry_label}</a>'
        ctxt = self.build_context()
        self.assertHTMLEqual(expected, TestEntry01().render(ctxt))

        # ----
        class TestEntry02(TestEntry01):
            permissions = ('creme_core', 'creme_config.can_admin')

        self.assertHTMLEqual(expected, TestEntry02().render(ctxt))

    def test_url_entry03(self):
        "With permissions KO."
        self.login(is_superuser=False)

        entry_label = 'Home'

        class TestEntry01(FixedURLEntry):
            id = 'creme_core-test'
            label = entry_label
            url_name = 'creme_core__home'
            permissions = 'creme_config'  # <===

        expected = f'<span class="ui-creme-navigation-text-entry forbidden">{entry_label}</span>'
        ctxt = self.build_context()
        self.assertHTMLEqual(expected, TestEntry01().render(ctxt))

        # ----
        class TestEntry02(TestEntry01):
            permissions = ('creme_core', 'creme_config')

        self.assertHTMLEqual(expected, TestEntry02().render(ctxt))

    def test_creation_entry01(self):
        self.login()
        self.assertIs(CreationEntry.single_instance, True)

        entry01 = CreationEntry()
        self.assertEqual(_('Create an entity'), entry01.label)

        with self.assertRaises(ValueError):
            entry01.url  # NOQA

        ctxt = self.build_context()
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

    def test_creation_entry02(self):
        "Not super-user, but allowed."
        self.login(is_superuser=False, creatable_models=[FakeContact])

        self.assertHTMLEqual(
            f'<a href="{reverse("creme_core__create_fake_contact")}">'
            f'{_("Create a contact")}'
            f'</a>',
            FakeContactCreationEntry().render(self.build_context()),
        )

    def test_creation_entry03(self):
        "Not allowed."
        self.login(is_superuser=False)  # creatable_models=[FakeContact]

        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-text-entry forbidden">'
            f'{_("Create a contact")}'
            f'</span>',
            FakeContactCreationEntry().render(self.build_context()),
        )

    def test_listview_entry01(self):
        self.login()
        self.assertIs(ListviewEntry.single_instance, True)

        ctxt = self.build_context()

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

    def test_listview_entry02(self):
        "Not super-user, but allowed."
        self.login(is_superuser=False)

        self.assertHTMLEqual(
            f'<a href="{reverse("creme_core__list_fake_contacts")}">Test Contacts</a>',
            FakeContactsEntry().render(self.build_context()),
        )

    def test_listview_entry03(self):
        "Not allowed."
        self.login(is_superuser=False, allowed_apps=['creme_config'])

        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">'
            'Test Contacts'
            '</span>',
            FakeContactsEntry().render(self.build_context()),
        )

    def test_container_entry01(self):
        self.login()
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
        self.assertEqual(
            '{} -> {}'.format(
                _('Label'),
                MaxLengthValidator.message % {
                    'limit_value': 50,
                    'show_value': 60,
                },
            ),
            ','.join(cm.exception.messages),
        )

        # ---
        ctxt = self.build_context()

        entry01 = ContainerEntry(data={'label': label})
        self.assertEqual('creme_core-container', entry01.id)
        self.assertEqual(label, entry01.label)
        self.assertFalse(entry01.is_required)
        self.assertListEqual([], [*entry01.children])

        render = entry01.render(ctxt)
        self.assertStartsWith(render, label)
        self.assertHTMLEqual('<ul></ul>', render[len(label):])

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
            entry02.render(ctxt)[len(label):],
        )

    def test_container_entry02(self):
        "MenuEntrySequence."
        self.login()

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

        ctxt = self.build_context()
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
            container.render(ctxt)[len(label):],
        )

    def test_separator0_entry(self):
        self.login()
        self.assertIs(Separator0Entry.single_instance, False)

        entry = Separator0Entry()
        self.assertEqual('creme_core-separator0', entry.id)
        self.assertEqual(_('Separator'),          entry.label)
        self.assertEqual(0,                       entry.level)

        self.assertEqual('', entry.render(self.build_context()))

    def test_separator1_entry01(self):
        "Empty label."
        self.login()
        self.assertEqual(_('Add a separator'), Separator1Entry.creation_label)
        self.assertIs(Separator1Entry.single_instance, False)

        entry = Separator1Entry()
        self.assertEqual('creme_core-separator1', entry.id)
        self.assertEqual('creme_core-separator1', entry.type)
        # self.assertEqual('----', entry.label)
        self.assertEqual('', entry.label)
        self.assertEqual(1,  entry.level)

        self.assertEqual('', entry.render(self.build_context()))

    def test_separator1_entry02(self):
        "With label."
        self.login()

        label = 'My group'
        entry = Separator1Entry(data={'label': label})
        self.assertEqual(label, entry.label)
        self.assertHTMLEqual(
            f'<span class="ui-creme-navigation-title">{label}</span>',
            entry.render(self.build_context()),
        )

    def test_custom_url_entry01(self):
        self.login()
        label = 'Python'
        url = 'http://www.python.org'

        self.assertEqual(_('Add an URL entry'), CustomURLEntry.creation_label)
        self.assertIs(CustomURLEntry.single_instance, False)

        # ---
        validate = CustomURLEntry.validate

        with self.assertRaises(ValidationError) as cm1:
            validate(data={'label': label})
        self.assertEqual(
            '{} -> {}'.format(_('URL'), _('This field is required.')),
            ','.join(cm1.exception.messages),
        )

        with self.assertRaises(ValidationError) as cm2:
            validate({'label': label, 'url': '1234'})
        self.assertEqual(
            '{} -> {}'.format(_('URL'), _('Enter a valid URL.')),
            ','.join(cm2.exception.messages),
        )

        with self.assertRaises(ValidationError) as cm3:
            validate({'label': '', 'url': url})
        self.assertEqual(
            '{} -> {}'.format(_('Label'), _('This field is required.')),
            ','.join(cm3.exception.messages),
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
            f'<a href="{url}">{label}</a>',
            entry.render(self.build_context()),
        )

    def test_custom_url_entry02(self):
        "No data."
        self.login()

        label = 'Python'
        entry = CustomURLEntry(data={'label': label})
        self.assertEqual(label, entry.label)
        self.assertEqual('', entry.url)
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">{}</span>'.format(
                _('{label} (broken configuration)').format(label=label),
            ),
            entry.render(self.build_context()),
        )

    def test_custom_url_entry03(self):
        "No url."
        self.login()

        label = 'Python'
        entry = CustomURLEntry(data={'label': label, 'foo': 'bar'})
        self.assertEqual(label, entry.label)
        self.assertEqual('', entry.url)

    def test_home_entry(self):
        self.login()
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
            entry.render(self.build_context()),
        )

    def test_jobs_entry(self):
        self.login()
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
            entry.render(self.build_context()),
        )

    def test_trash_entry(self):
        user = self.login()
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
            entry.render(self.build_context()),
        )

    def test_logout_entry(self):
        self.login()
        self.assertTrue(LogoutEntry.single_instance)

        entry = LogoutEntry()
        self.assertEqual('creme_core-logout', entry.id)
        self.assertEqual(_('Log out'), entry.label)
        self.assertEqual(reverse('creme_logout'), entry.url)

    def test_creme_entry(self):
        self.login()
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
        assertInChildren(LogoutEntry)

        render = entry.render(self.build_context())
        self.assertStartsWith(render, label)

        tree = self.get_html_tree(render[len(label):])
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

    def test_recent_entities_entry01(self):
        user = self.login()
        self.assertTrue(RecentEntitiesEntry.single_instance)

        contact1 = user.linked_contact
        contact2 = self.other_user.linked_contact

        ctxt = self.build_context()
        request = ctxt['request']
        LastViewedItem(request, contact1)
        LastViewedItem(request, contact2)

        entry = RecentEntitiesEntry()
        self.assertEqual(0, entry.level)

        entry_id = 'creme_core-recent_entities'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Recent entities')
        self.assertEqual(entry_label, entry.label)

        render = entry.render(ctxt)
        self.assertStartsWith(render, entry_label)
        self.assertHTMLEqual(
            f'<ul>'
            # f'  <li><a href="{contact2.get_absolute_url()}">{contact2}</a></li>'
            f'  <li>'
            f'    <a href="{contact2.get_absolute_url()}">'
            f'      <span class="ui-creme-navigation-ctype">{contact2.entity_type}</span>'
            f'      {contact2}'
            f'    </a>'
            f'  </li>'
            # f'  <li><a href="{contact1.get_absolute_url()}">{contact1}</a></li>'
            f'  <li>'
            f'    <a href="{contact1.get_absolute_url()}">'
            f'      <span class="ui-creme-navigation-ctype">{contact1.entity_type}</span>'
            f'      {contact1}'
            f'    </a>'
            f'  </li>'
            f'</ul>',
            render[len(entry_label):],
        )

    def test_recent_entities_entry02(self):
        self.login()
        entry = RecentEntitiesEntry()

        entry_label = _('Recent entities')
        self.assertEqual(entry_label, entry.label)

        render = entry.render(self.build_context())
        self.assertStartsWith(render, entry_label)
        self.assertHTMLEqual(
            '<ul>'
            '   <li><span class="ui-creme-navigation-text-entry">{}</span></li>'
            '</ul>'.format(escape(_('No recently visited entity'))),
            render[len(entry_label):],
        )

    def test_quick_forms_entries(self):
        user = self.login(is_superuser=False)

        seq = QuickFormsEntries()
        self.assertIsInstance(seq, MenuEntrySequence)
        self.assertEqual('creme_core-quick_forms', seq.id)
        self.assertEqual(_('*Quick forms*'),       seq.label)
        self.assertEqual(1,                        seq.level)
        self.assertFalse(seq.single_instance)
        self.assertIs(quick_forms.quickforms_registry, seq.quickforms_registry)

        with self.assertNoException():
            cdata = QuickFormsEntries.validate({})
        self.assertDictEqual({}, cdata)

        registry = quick_forms.QuickFormsRegistry()
        seq.quickforms_registry = registry

        entries1 = [*seq]
        self.assertEqual(1, len(entries1))

        entry11 = entries1[0]
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
            entry21.render(self.build_context()),
        )

        self.role.creatable_ctypes.set([contact_ctype])
        user = self.refresh(self.user)
        self.assertTrue(user.has_perm_to_create(FakeContact))
        self.assertHTMLEqual(
            f'<a href="#" data-href="{url1}" class="quickform-menu-link">{label1}</a>',
            entry21.render(self.build_context(user=user)),
        )

        self.assertEqual(FakeOrganisation, entries2[1].model)

    def test_creation_forms_entry01(self):
        user = self.create_user()
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

    def test_creation_forms_entry02(self):
        "Simplified API."
        user = self.create_user()
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

    def test_creation_forms_entry03(self):
        "Link priority."
        user = self.create_user()
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

    def test_creation_forms_entry04(self):
        "Remove Link."
        user = self.create_user()
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

    def test_creation_forms_entry05(self):
        "Group priority."
        user = self.create_user()
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

    def test_creation_forms_entry06(self):
        "Remove Group."
        user = self.create_user()
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

    def test_creation_forms_entry07(self):
        "Credentials."
        user = self.login(is_superuser=False, creatable_models=[FakeContact])
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

    def test_creation_forms_entry08(self):
        "ID uniqueness."
        registry = CreationMenuRegistry()

        group = registry.get_or_create_group(
            'persons', 'Directory',
        ).add_link('add_contact', FakeContact)

        with self.assertRaises(ValueError):
            group.add_link('add_contact', FakeContact, label='Contact')

    def test_registry01(self):
        item1 = MenuConfigItem(id=1, entry_id=CremeEntry.id, order=0)
        items = [item1]

        registry = MenuRegistry()
        self.assertListEqual([], registry.get_entries(items))
        self.assertListEqual([], [*registry.entry_classes])
        self.assertIsNone(registry.get_class(CremeEntry.id))

        # -------------
        registry.register(FakeContactsEntry, CremeEntry)
        self.assertSetEqual({FakeContactsEntry, CremeEntry}, {*registry.entry_classes})

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

    def test_registry02(self):
        "Container with children."
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

    def test_registry03(self):
        "Container does not accepts children."
        container_item = MenuConfigItem(id=1, entry_id=RecentEntitiesEntry.id)
        sub_item = MenuConfigItem(
            id=2, entry_id=FakeContactsEntry.id, parent_id=container_item.id
        )
        registry = MenuRegistry().register(
            RecentEntitiesEntry, FakeContactsEntry
        )

        entries = registry.get_entries([container_item, sub_item])
        self.assertEqual(1, len(entries))

        entry = entries[0]
        self.assertIsInstance(entry, RecentEntitiesEntry)
        self.assertListEqual([], [*entry.children])

    def test_global_registry(self):
        entry_classes = {*menu_registry.entry_classes}
        self.assertIn(ContainerEntry,        entry_classes)
        self.assertIn(Separator0Entry,       entry_classes)
        self.assertIn(Separator1Entry,       entry_classes)
        self.assertIn(CustomURLEntry,        entry_classes)
        self.assertIn(CremeEntry,            entry_classes)
        self.assertIn(QuickFormsEntries,     entry_classes)
        self.assertIn(EntitiesCreationEntry, entry_classes)
        self.assertIn(RecentEntitiesEntry,   entry_classes)


# class MenuTestCase(CremeTestCase):
#     theme = 'icecream'
#
#     def setUp(self):
#         super().setUp()
#         self.factory = RequestFactory()
#         self.maxDiff = None
#
#     def build_context(self):
#         user = getattr(self, 'user', None) or self.login()
#
#         return {
#             'request': self.factory.get('/'),
#             'user': user,
#             'THEME_NAME': self.theme,
#         }
#
#     def test_item_id(self):
#         item_id = 'persons-add_contact'
#         self.assertEqual(item_id, ViewableItem(item_id).id)
#
#         # Invalid id
#         with self.assertRaises(ValueError):
#             ViewableItem('persons-add_"contact"')  # " char is forbidden
#
#         with self.assertRaises(ValueError):
#             ViewableItem("persons-add_'contact'")  # ' char is forbidden
#
#     def test_item_label(self):
#         self.assertEqual('', ViewableItem('add_contact').label)  # TODO: None ??
#
#         my_label = 'Add a contact'
#         self.assertEqual(my_label, ViewableItem('add_contact', label=my_label).label)
#
#     def test_item_perm(self):
#         self.assertIsNone(ViewableItem('add_contact').perm)
#
#         my_perm = 'persons.add_contact'
#         self.assertEqual(my_perm, ViewableItem('add_contact', perm=my_perm).perm)
#
#     def test_item_icon01(self):
#         item = ViewableItem('add_contact')
#         self.assertIsNone(item.icon)
#         self.assertEqual('', item.icon_label)
#
#     def test_item_icon02(self):
#         my_icon = 'contact'
#         my_icon_label = 'Contact'
#         item = ViewableItem('add_contact', icon=my_icon, icon_label=my_icon_label)
#         self.assertEqual(my_icon, item.icon)
#         self.assertEqual(my_icon_label, item.icon_label)
#
#     def test_item_icon03(self):
#         "No icon_label => use label."
#         my_label = 'Contact'
#         item = ViewableItem('add_contact', icon='contact', label=my_label)
#         self.assertEqual(my_label, item.icon_label)
#
#     def test_add_items01(self):
#         menu = Menu()
#         item1 = ViewableItem('add_contact')
#         self.assertIsNone(item1.priority)
#
#         item2 = ViewableItem('add_orga')
#
#         menu.add(item1).add(item2)
#         self.assertListEqual([item1, item2], [*menu])
#
#         self.assertEqual(1, item1.priority)
#
#     def test_add_items02(self):
#         "Duplicated ID."
#         menu = Menu()
#         id_ = 'add_contact'
#         item1 = ViewableItem(id_)
#         item2 = ViewableItem(id_)
#
#         menu.add(item1)
#
#         with self.assertRaises(ValueError):
#             menu.add(item2)
#
#     def test_group_id(self):
#         group_id = 'persons'
#         self.assertEqual(group_id, ItemGroup(group_id).id)
#
#         # Invalid id
#         with self.assertRaises(ValueError):
#             ItemGroup('"persons"-app')  # " char ...
#
#     def test_group_label(self):
#         self.assertEqual('', ItemGroup('creations').label)
#
#         my_label = 'Add entities...'
#         self.assertEqual(my_label, ItemGroup('creations', label=my_label).label)
#
#     def test_add_groups(self):
#         menu = Menu()
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         item3 = ViewableItem('add_activity')
#
#         group.add(item2).add(item3)
#         menu.add(item1).add(group)
#         self.assertListEqual([item1, item2, item3], [*menu])
#
#         # Add an Item already added
#         with self.assertRaises(ValueError):
#             group.add(item2)
#
#     def test_url_item01(self):
#         my_label = 'Add a contact'
#         url = '/persons/add_a_contact'
#         item = URLItem('add_contact', label=my_label, url=url)
#         self.assertEqual(my_label, item.label)
#         self.assertEqual(url,      item.url)
#
#         url = '/tests/customers'
#         item.url = lambda: url
#         self.assertEqual(url, item.url)
#
#     def test_url_item02(self):
#         "For list-view."
#         id_ = 'add_contact'
#         item = URLItem.list_view(id_, model=FakeContact)
#         self.assertIsInstance(item, URLItem)
#         self.assertEqual(id_,               item.id)
#         self.assertEqual('/tests/contacts', item.url)
#         self.assertEqual('Test Contacts',  item.label)
#         self.assertEqual('creme_core',      item.perm)
#
#         # Custom attributes
#         label = 'My contacts'
#         url = '/tests/my_contacts'
#         perm = 'persons'
#         item = URLItem.list_view(
#             id_, model=FakeContact, perm=perm, label=label, url=url,
#         )
#         self.assertEqual(label, item.label)
#         self.assertEqual(url,   item.url)
#         self.assertEqual(perm,  item.perm)
#
#     def test_url_item03(self):
#         "For creation view."
#         id_ = 'add_contact'
#         item = URLItem.creation_view(id_, model=FakeContact)
#         self.assertIsInstance(item, URLItem)
#         self.assertEqual(id_,                          item.id)
#         self.assertEqual('/tests/contact/add',         item.url)
#         self.assertEqual('Test Contact',               item.label)
#         self.assertEqual('creme_core.add_fakecontact', item.perm)
#
#         # Custom attributes
#         label = 'My contact'
#         url = '/tests/my_contacts/add'
#         perm = 'persons'
#         item = URLItem.creation_view(
#             id_, model=FakeContact, perm=perm, label=label, url=url,
#         )
#         self.assertEqual(label, item.label)
#         self.assertEqual(url,   item.url)
#         self.assertEqual(perm,  item.perm)
#
#     def test_add_items_to_group01(self):
#         group = ItemGroup('persons')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#
#         group.add(item1)
#         group.add(item2)
#
#         self.assertListEqual([item1, item2], [*group])
#
#     def test_add_items_to_group02(self):
#         "Priority."
#         group = ItemGroup('persons')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         item3 = ViewableItem('add_address')
#         item4 = ViewableItem('add_customer')
#         item5 = ViewableItem('add_shipping_addr')
#         item6 = ViewableItem('add_billing_addr')
#
#         group.add(item1)
#         group.add(item2, priority=1)
#         self.assertListEqual([item1, item2], [*group])
#
#         group.add(item3, priority=3)
#         group.add(item4, priority=2)
#         self.assertListEqual([item1, item2, item4, item3], [*group])
#         self.assertEqual(3, item3.priority)
#
#         # Not property => end
#         group.add(item5)
#         group.add(item6, priority=2)  # priority of previous has been set
#         self.assertListEqual([item1, item2, item4, item6, item3, item5], [*group])
#
#     def test_add_items_to_group03(self):
#         "Several items at once."
#         group = ItemGroup('persons')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#
#         group.add(item2, item1)
#         self.assertListEqual([item2, item1], [*group])
#
#     def test_add_items_to_group04(self):
#         "First has priority."
#         group = ItemGroup('persons')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#
#         group.add(item1, priority=10)
#         group.add(item2, priority=1)
#         self.assertListEqual([item2, item1], [*group])
#
#     def test_container_get01(self):
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         group.add(item1).add(item2)
#
#         self.assertEqual(item1, group.get(item1.id))
#         self.assertEqual(item2, group.get(item2.id))
#         self.assertRaises(KeyError, group.get, 'unknown_id')
#
#     def test_container_get02(self):
#         menu = Menu()
#         container1 = ContainerItem('creations')
#         container2 = ContainerItem('editions')
#         group1 = ItemGroup('add_persons')
#         group2 = ItemGroup('add_tickets')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         item3 = ViewableItem('add_ticket')
#
#         menu.add(
#             container1.add(group1.add(item1).add(item2)).add(group2.add(item3))
#         ).add(container2)
#
#         self.assertEqual(group1, menu.get(container1.id, group1.id))
#         self.assertEqual(item1,  menu.get(container1.id, group1.id, item1.id))
#         self.assertEqual(item3,  menu.get(container1.id, group2.id, item3.id))
#         self.assertRaises(KeyError, menu.get, container2.id, group1.id)
#         self.assertRaises(KeyError, menu.get, container1.id, group1.id, 'unknown_id')
#         # 'item1' is not a container
#         self.assertRaises(KeyError, menu.get, container1.id, group1.id, item1.id, 'whatever')
#
#     def test_remove_items_from_group(self):
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         item3 = ViewableItem('add_event')
#         item4 = ViewableItem('add_activity')
#         group.add(item1, item2, item3, item4)
#
#         group.remove(item2.id)
#         self.assertListEqual([item1, item3, item4], [*group])
#
#         group.remove(item1.id, item4.id)
#         self.assertListEqual([item3], [*group])
#
#         group.remove('unknown_id')  # TODO: exception ?? boolean ??
#
#         with self.assertNoException():
#             group.add(item1)
#
#     def test_clear_group(self):
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#
#         group.add(item1).add(item2)
#         group.clear()
#         self.assertFalse([*group])
#
#         with self.assertNoException():
#             group.add(item1)
#
#     def test_pop_group(self):
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         group.add(item1, priority=2).add(item2, priority=3)
#
#         item2b = group.pop(item2.id)
#         self.assertEqual(item2, item2b)
#         self.assertListEqual([item1], [*group])
#
#         self.assertRaises(KeyError, group.pop, item2.id)
#
#         group.add(item2b, priority=1)
#         self.assertListEqual([item2b, item1], [*group])
#
#     def test_change_priority_group(self):
#         group = ItemGroup('creations')
#         item1 = ViewableItem('add_contact')
#         item2 = ViewableItem('add_orga')
#         item3 = ViewableItem('add_event')
#         group.add(item1, priority=2).add(item2, priority=3).add(item3, priority=4)
#
#         group.change_priority(1, item3.id, item2.id)
#         self.assertListEqual([item3, item2, item1], [*group])
#
#     def test_container_item(self):
#         my_label = 'Creations...'
#         container = ContainerItem('persons', label=my_label)
#         self.assertEqual(my_label, container.label)
#
#         child1 = ViewableItem('persons-add_contact')
#         child2 = ViewableItem('persons-add_orga')
#
#         container.add(child2, child1)
#         self.assertListEqual([child2, child1], [*container])
#
#     def test_get_or_create(self):
#         menu = Menu()
#
#         id_ = 'analysis'
#         label = 'Analysis'
#         container1 = menu.get_or_create(
#             ContainerItem, id_, priority=5, defaults={'label': label},
#         )
#         self.assertIsInstance(container1, ContainerItem)
#         self.assertEqual(id_,   container1.id)
#         self.assertEqual(label, container1.label)
#
#         container2 = menu.get_or_create(
#             ContainerItem, id_, priority=5, defaults={'label': label + ' #2'},
#         )
#         self.assertIs(container1, container2)
#         self.assertEqual(label, container2.label)
#         self.assertListEqual([container1], [*menu])
#
#         with self.assertRaises(ValueError):
#             menu.get_or_create(
#                 ItemGroup, id_, priority=5, defaults={'label': label},
#             )
#
#         # defaults is None
#         gid = 'my_group'
#         group = menu.get_or_create(ItemGroup, gid, priority=5)
#         self.assertIsInstance(group, ItemGroup)
#         self.assertEqual(gid, group.id)
#         self.assertFalse(group.label)
#
#     def test_creation_forms_item01(self):
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         cfi.get_or_create_group(
#             'persons', 'Directory',
#         ).add_link(
#             'add_contact', label='Contact', url='/tests/contact/add',
#             perm='creme_core.add_fakecontact',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': 'Contact', 'url': '/tests/contact/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group(
#             'persons', 'Directory',
#         ).add_link(
#             'add_orga', label='Organisation', url='/tests/organisation/add',
#             perm='creme_core.add_fakeorganisation',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     },
#                 ]
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group(
#             'activities', 'Activities',
#         ).add_link(
#             'add_pcall', label='Phone call', url='/tests/phone_call/add',
#             perm='creme_core.add_fakeactivity',
#         ).add_link(
#             'add_meeting', label='Meeting', url='/tests/meeting/add',
#             perm='creme_core.add_fakeactivity',
#         )
#         cfi.get_or_create_group(
#             'tools', 'Tools',
#         ).add_link(
#             'add_doc', label='Document', url='/tests/document/add',
#             perm='creme_core.add_fakedocument',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     },
#                 ], [
#                     {
#                         'label': 'Activities',
#                         'links': [
#                             {'label': 'Phone call', 'url': '/tests/phone_call/add'},
#                             {'label': 'Meeting',    'url': '/tests/meeting/add'},
#                         ],
#                     }, {
#                         'label': 'Tools',
#                         'links': [{'label': 'Document', 'url': '/tests/document/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group(
#             'analysis', 'Analysis',
#         ).add_link(
#             'add_report', label='Report', url='/tests/report/add',
#             perm='creme_core.add_fakereport',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     }, {
#                         'label': 'Activities',
#                         'links': [
#                             {'label': 'Phone call', 'url': '/tests/phone_call/add'},
#                             {'label': 'Meeting',    'url': '/tests/meeting/add'},
#                         ],
#                     },
#                 ], [
#                     {
#                         'label': 'Tools',
#                         'links': [{'label': 'Document', 'url': '/tests/document/add'}],
#                     }, {
#                         'label': 'Analysis',
#                         'links': [{'label': 'Report', 'url': '/tests/report/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group(
#             'management', 'Management',
#         ).add_link(
#             'add_invoice', label='Invoice', url='/tests/invoice/add',
#             perm='creme_core.add_fakeinvoice',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     },
#                 ], [
#                     {
#                         'label': 'Activities',
#                         'links': [
#                             {'label': 'Phone call', 'url': '/tests/phone_call/add'},
#                             {'label': 'Meeting',    'url': '/tests/meeting/add'},
#                         ],
#                     }, {
#                         'label': 'Tools',
#                         'links': [{'label': 'Document', 'url': '/tests/document/add'}],
#                     },
#                 ], [
#                     {
#                         'label': 'Analysis',
#                         'links': [{'label': 'Report', 'url': '/tests/report/add'}],
#                     }, {
#                         'label': 'Management',
#                         'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
#                     },
#                 ]
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group('commercial', 'Commercial') \
#            .add_link('add_act', label='Act', url='/tests/act/add', perm='creme_core')
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     }, {
#                         'label': 'Activities',
#                         'links': [
#                             {'label': 'Phone call', 'url': '/tests/phone_call/add'},
#                             {'label': 'Meeting',    'url': '/tests/meeting/add'},
#                         ],
#                     },
#                 ], [
#                     {
#                         'label': 'Tools',
#                         'links': [{'label': 'Document', 'url': '/tests/document/add'}],
#                     }, {
#                         'label': 'Analysis',
#                         'links': [{'label': 'Report', 'url': '/tests/report/add'}],
#                     },
#                 ], [
#                     {
#                         'label': 'Management',
#                         'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
#                     }, {
#                         'label': 'Commercial',
#                         'links': [{'label': 'Act', 'url': '/tests/act/add'}],
#                     },
#                 ]
#             ],
#             cfi.as_grid(user)
#         )
#
#         cfi.get_or_create_group(
#             'marketing', 'Marketing',
#         ).add_link(
#             'add_campaign', label='Campaign', url='/tests/campaign/add', perm='creme_core',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     }, {
#                         'label': 'Activities',
#                         'links': [
#                             {'label': 'Phone call', 'url': '/tests/phone_call/add'},
#                             {'label': 'Meeting',    'url': '/tests/meeting/add'},
#                         ],
#                     },
#                 ], [
#                     {
#                         'label': 'Tools',
#                         'links': [{'label': 'Document', 'url': '/tests/document/add'}],
#                     }, {
#                         'label': 'Analysis',
#                         'links': [{'label': 'Report', 'url': '/tests/report/add'}],
#                     },
#                 ], [
#                     {
#                         'label': 'Management',
#                         'links': [{'label': 'Invoice', 'url': '/tests/invoice/add'}],
#                     }, {
#                         'label': 'Commercial',
#                         'links': [{'label': 'Act', 'url': '/tests/act/add'}],
#                     }, {
#                         'label': 'Marketing',
#                         'links': [{'label': 'Campaign', 'url': '/tests/campaign/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#     def test_creation_forms_item02(self):
#         "Simplified API"
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         cfi.get_or_create_group('persons', 'Directory').add_link('add_contact', FakeContact)
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#         # ----
#         cfi = CreationFormsItem('any_forms', label='Other types')
#
#         label = 'Contact'
#         url = '/tests/customer/add'
#         cfi.get_or_create_group(
#             'persons', 'Directory',
#         ).add_link('add_contact', FakeContact, label=label, url=url)
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': label, 'url': url}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#         # ----
#         group = CreationFormsItem(
#             'any_forms', label='Other types',
#         ).get_or_create_group('persons', 'Directory')
#
#         with self.assertRaises(TypeError):
#             group.add_link('add_contact', label=label, url=url)  # No model + missing perm
#
#     def test_creation_forms_item03(self):
#         "Link priority."
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#         group = cfi.get_or_create_group('persons', 'Directory')
#
#         group.add_link(
#             'add_contact', FakeContact,      priority=10,
#         ).add_link(
#             'add_orga',    FakeOrganisation, priority=5,
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
#                             {'label': 'Test Contact',      'url': '/tests/contact/add'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         group.add_link(
#             'add_customer', label='Customer', url='/tests/customer/add',
#             perm='creme_core.add_fakecontact',
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
#                             {'label': 'Test Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Customer',          'url': '/tests/customer/add'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         group.add_link(
#             'add_propect', label='Prospect', url='/tests/prospect/add',
#             perm='creme_core.add_fakecontact', priority=15,
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
#                             {'label': 'Test Contact',      'url': '/tests/contact/add'},
#                             {'label': 'Customer',          'url': '/tests/customer/add'},
#                             {'label': 'Prospect',          'url': '/tests/prospect/add'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         group.change_priority(1, 'add_propect', 'add_customer')
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Prospect',          'url': '/tests/prospect/add'},
#                             {'label': 'Customer',          'url': '/tests/customer/add'},
#                             {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
#                             {'label': 'Test Contact',      'url': '/tests/contact/add'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user)
#         )
#
#         with self.assertRaises(KeyError):
#             group.change_priority(2, 'add_customer', 'unknown')
#
#     def test_creation_forms_item04(self):
#         "Remove Link."
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#         group = cfi.get_or_create_group('persons', 'Directory')
#
#         group.add_link(
#             'add_contact', FakeContact,
#         ).add_link(
#             'add_orga', FakeOrganisation,
#         ).add_link(
#             'add_prospect', label='Prospect', url='/tests/propect/add',
#             perm='creme_core.add_fakecontact',
#         )
#
#         group.remove('add_contact', 'add_prospect', 'invalid')
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Test Organisation', 'url': '/tests/organisation/add'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#     def test_creation_forms_item05(self):
#         "Group priority."
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         cfi.get_or_create_group(
#             'persons', 'Directory', priority=10,
#         ).add_link('add_contact', FakeContact)
#         cfi.get_or_create_group(
#             'tools', 'Tools', priority=2,
#         ).add_link('add_doc', FakeDocument)
#
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Tools',
#                         'links': [{'label': 'Test Document', 'url': ''}],
#                     },
#                 ], [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#         cfi.change_priority(1, 'persons')
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
#                     },
#                 ], [
#                     {
#                         'label': 'Tools',
#                         'links': [{'label': 'Test Document', 'url': ''}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#     def test_creation_forms_item06(self):
#         "Remove Group."
#         user = self.create_user()
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         cfi.get_or_create_group('tools', 'Tools').add_link('add_doc', FakeDocument)
#         cfi.get_or_create_group('persons', 'Directory').add_link('add_contact', FakeContact)
#         cfi.get_or_create_group('activities', 'Activities').add_link('add_act', FakeActivity)
#
#         cfi.remove('tools', 'activities', 'unknown')
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [{'label': 'Test Contact', 'url': '/tests/contact/add'}],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#     def test_creation_forms_item07(self):
#         "Credentials."
#         user = self.login(is_superuser=False, creatable_models=[FakeContact])
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         cfi.get_or_create_group(
#             'persons', 'Directory',
#         ).add_link(
#             'add_contact', FakeContact,
#         ).add_link(
#             'add_orga', FakeOrganisation,
#         )
#         self.assertListEqual(
#             [
#                 [
#                     {
#                         'label': 'Directory',
#                         'links': [
#                             {'label': 'Test Contact', 'url': '/tests/contact/add'},
#                             {'label': 'Test Organisation'},
#                         ],
#                     },
#                 ],
#             ],
#             cfi.as_grid(user),
#         )
#
#     def test_creation_forms_item08(self):
#         "ID uniqueness."
#         cfi = CreationFormsItem('any_forms', label='Other type of entity')
#
#         group = cfi.get_or_create_group(
#             'persons', 'Directory',
#         ).add_link('add_contact', FakeContact)
#
#         with self.assertRaises(ValueError):
#             group.add_link('add_contact', FakeContact, label='Contact')
#
#     def test_render_url_item01(self):
#         "URLItem with icon."
#         url = '/'
#         icon = 'creme'
#         label = 'Home'
#         item = URLItem('home', url=url, icon=icon, icon_label=label)
#
#         tree = self.get_html_tree(item.render(self.build_context()))
#         a_node = tree.find('.//a')
#         self.assertEqual(url, a_node.get('href'))
#
#         children = [*a_node]
#         self.assertEqual(1, len(children))
#
#         img_node = children[0]
#         self.assertEqual('img',              img_node.tag)
#         self.assertEqual('header-menu-icon', img_node.get('class'))
#         self.assertEqual(label,              img_node.get('alt'))
#         self.assertEqual(label,              img_node.get('title'))
#         self.assertIn(icon,                  img_node.get('src', ''))
#         self.assertFalse(img_node.tail)
#
#     def test_render_url_item02(self):
#         "URLItem with icon and label."
#         icon = 'creme'
#         my_label = 'HOME'
#         item = URLItem(
#             'home',
#             url='/', label=my_label, icon=icon, icon_label='Home', perm='creme_core',
#         )
#
#         tree = self.get_html_tree(item.render(self.build_context()))
#         img_node = tree.find('.//a/img')
#         self.assertEqual('header-menu-icon', img_node.get('class'))
#         self.assertEqual(my_label,           img_node.tail)
#
#     def test_render_url_item03(self):
#         "Not allowed (string perm)."
#         self.login(is_superuser=False, allowed_apps=['creme_core'])
#
#         icon = 'creme'
#         my_label = 'HOME'
#         item = URLItem(
#             'home',
#             url='/', label=my_label, icon=icon, icon_label='Home',
#             perm='creme_core.add_fakecontact',
#         )
#
#         tree = self.get_html_tree(item.render(self.build_context()))
#         span_node = tree.find('.//span')
#         self.assertEqual(
#             'ui-creme-navigation-text-entry forbidden',
#             span_node.get('class'),
#         )
#
#         children = [*span_node]
#         self.assertEqual(1, len(children))
#         self.assertEqual('img', children[0].tag)
#
#     def test_render_url_item04(self):
#         "Perm is callable."
#         self.login(is_superuser=False)
#
#         url = '/creme/add_contact'
#         item = URLItem(
#             'home',
#             url=url, label='Create contact', perm=lambda user: user.is_superuser,
#         )
#
#         tree1 = self.get_html_tree(item.render(self.build_context()))
#         span_node = tree1.find('.//span')
#         self.assertEqual(
#             'ui-creme-navigation-text-entry forbidden',
#             span_node.get('class'),
#         )
#
#         # ---
#         item.perm = lambda user: True
#         tree2 = self.get_html_tree(item.render(self.build_context()))
#         self.assertIsNone(tree2.find('.//span'))
#
#         a_node = tree2.find('.//a')
#         self.assertEqual(url, a_node.get('href'))
#
#     def test_render_label_item(self):
#         item_id = 'tools-title'
#         label = 'Important title'
#         item = LabelItem(item_id, label=label)
#
#         self.assertHTMLEqual(
#             f'<span class="ui-creme-navigation-text-entry">{label}</span>',
#             item.render(self.build_context()),
#         )
#
#     def test_render_container_item01(self):
#         "No icon."
#         context = self.build_context()
#
#         label = 'Creations'
#         container = ContainerItem(
#             'persons', label=label,
#         ).add(
#             URLItem('contacts', url='/persons/contacts',      label='List of contacts'),
#             URLItem('orgas',    url='/persons/organisations', label='List of organisations'),
#         )
#
#         render = container.render(context)
#         self.assertStartsWith(render, label)
#         self.assertHTMLEqual(
#             '<ul>'
#             '  <li class="ui-creme-navigation-item-id_contacts ui-creme-navigation-item-level1">'
#             '    <a href="/persons/contacts">List of contacts</a>'
#             '  </li>'
#             '  <li class="ui-creme-navigation-item-id_orgas ui-creme-navigation-item-level1">'
#             '    <a href="/persons/organisations">List of organisations</a>'
#             '  </li>'
#             '</ul>',
#             render[len(label):],
#         )
#
#     def test_render_container_item02(self):
#         "No icon."
#         context = self.build_context()
#
#         label = 'Contacts'
#         icon = 'contact'
#         icon_label = 'Contact'
#         parent = ContainerItem(
#             'persons', label=label, icon=icon, icon_label=icon_label,
#         ).add(
#             URLItem('home', url='/persons/contacts', label='List of contacts'),
#         )
#
#         tree = self.get_html_tree(parent.render(context, level=1))
#
#         # ElementTree.dump(elt) >>>
#         # <html><head /><body>
#         #         <img alt="Contact" class="header-menu-icon"
#         #              src="/static_media/icecream/images/contact_16-....png"
#         #              title="Contact" width="16px" />
#         #         Contacts
#         #         <ul>
#         #             <li class="ui-creme-navigation-item-level2
#         #                 ui-creme-navigation-item-id_home">
#         #                  <a href="/persons/contacts">List of contacts</a>
#         #             </li>
#         #         </ul>
#         # </body>
#         img_node = tree.find('.//img')
#         self.assertIsNotNone(img_node, 'No <img> tag.')
#         self.assertEqual('header-menu-icon', img_node.get('class'))
#         self.assertEqual(icon_label,         img_node.get('alt'))
#         self.assertEqual(icon_label,         img_node.get('title'))
#         self.assertIn(icon,                  img_node.get('src', ''))
#         self.assertIn(label,                 img_node.tail)
#
#         ul_node = tree.find('.//ul')
#         self.assertIsNotNone(ul_node, 'No <ul> tag.')
#         self.assertHTMLEqual(
#             '<ul>'
#             '  <li class="ui-creme-navigation-item-id_home ui-creme-navigation-item-level2">'
#             '    <a href="/persons/contacts">List of contacts</a>'
#             '  </li>'
#             '</ul>',
#             ElementTree.tostring(ul_node).decode(),
#         )
#
#     def test_render_menu(self):
#         menu = Menu().add(
#             URLItem('contacts', url='/persons/contacts',      label='List of contacts'),
#             URLItem('orgas',    url='/persons/organisations', label='List of organisations'),
#         )
#         self.assertHTMLEqual(
#             '<ul class="ui-creme-navigation">'
#             '  <li class="ui-creme-navigation-item-level0 ui-creme-navigation-item-id_contacts">'
#             '    <a href="/persons/contacts">List of contacts</a>'
#             '  </li>'
#             '  <li class="ui-creme-navigation-item-level0 ui-creme-navigation-item-id_orgas">'
#             '    <a href="/persons/organisations">List of organisations</a>'
#             '  </li>'
#             '</ul>',
#             menu.render(self.build_context()),
#         )
