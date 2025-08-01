from copy import copy, deepcopy
from functools import partial
from json import dumps as json_dump

from django import forms
from django.forms.fields import InvalidJSONInput  # CallableChoiceIterator
from django.urls import reverse
from django.utils.choices import CallableChoiceIterator
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.menu import MenuEntryForm
from creme.creme_core.gui.menu import (
    ContainerEntry,
    CustomURLEntry,
    MenuEntry,
    MenuRegistry,
    Separator1Entry,
    menu_registry,
)
from creme.creme_core.models import (
    CustomField,
    CustomFieldEnumValue,
    FakeContact,
    FakePosition,
    FakeSector,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_menu import (
    FakeContactCreationEntry,
    FakeContactsEntry,
    FakeOrganisationCreationEntry,
    FakeOrganisationsEntry,
)

from ..forms.fields import (
    BricksConfigField,
    CreatorEnumerableModelChoiceField,
    CreatorModelChoiceField,
    CreatorModelMultipleChoiceField,
    CustomMultiEnumChoiceField,
    MenuEntriesField,
)
from ..forms.widgets import CreatorModelChoiceWidget


class _ConfigFieldTestCase(CremeTestCase):
    @classmethod
    def create_admin(cls):
        return cls.create_user(
            index=0,
            role=cls.create_role(
                name='Admin',
                allowed_apps=['creme_core'],
                admin_4_apps=['creme_core'],
            ),
        )


class CreatorModelChoiceFieldTestCase(_ConfigFieldTestCase):
    ADD_URL = reverse(
        'creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.create_admin()

    def test_ok(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        sector = FakeSector.objects.first()
        self.assertEqual(sector, field.clean(str(sector.id)))

    def test_empty_required(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty_not_required(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all(), required=False)
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))

    def test_actions_not_admin(self):
        with self.assertNumQueries(0):
            field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        field.user = self.create_user(
            index=1,
            role=self.create_role(name='Industry', allowed_apps=['persons']),
        )

        render_str = field.widget.render('sector', None)
        self.assertIn(_('Cannot create'), render_str)

        field.user = None
        render_str = field.widget.render('sector', None)
        self.assertNotIn(_('Cannot create'), render_str)

    def test_actions_admin(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        field.user = self.create_user(
            index=1,
            role=self.create_role(name='CEO', admin_4_apps=['creme_core']),
        )

        render_str = field.widget.render('sector', None)
        self.assertIn(self.ADD_URL, render_str)
        self.assertIn(str(FakeSector.creation_label), render_str)

        field.user = None
        render_str = field.widget.render('sector', None)
        self.assertNotIn(self.ADD_URL, render_str)

    def test_actions_admin_no_creatable(self):
        field = CreatorModelChoiceField(queryset=FakePosition.objects.all())
        field.user = self.create_user(
            index=1,
            role=self.create_role(name='CEO', admin_4_apps=['creme_core']),
        )

        render_str = field.widget.render('position', None)
        self.assertNotIn(
            reverse(
                'creme_config__create_instance_from_widget',
                args=('creme_core', 'fake_position'),
            ),
            render_str,
        )
        self.assertNotIn(str(FakePosition.creation_label), render_str)

    def test_queryset01(self):
        "No action."
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        with self.assertNoException():
            choices = [*field.choices]

        self.assertListEqual(
            [
                ('', '---------'),
                *((p.pk, str(p)) for p in FakeSector.objects.all()),
            ],
            choices,
        )

    def test_queryset02(self):
        "With action."
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        field.user = self.admin

        with self.assertNoException():
            options = [*field.choices]

        self.assertListEqual(
            [
                ('', '---------'),
                *((p.pk, str(p)) for p in FakeSector.objects.all()),
            ],
            options,
        )

        # ------
        render_str = field.widget.render('sector', None)
        self.assertIn('---------', render_str)

        for sector in FakeSector.objects.all():
            self.assertIn(str(sector), render_str)

    def test_filtered_queryset01(self):
        "No action."
        pk = FakeSector.objects.first().pk
        field = CreatorModelChoiceField(queryset=FakeSector.objects.filter(pk=pk))

        with self.assertNoException():
            choices = [*field.choices]

        self.assertListEqual(
            [
                ('', '---------'),
                (pk, FakeSector.objects.get(pk=pk).title),
            ],
            choices,
        )

    def test_filtered_queryset02(self):
        "With action."
        first = FakeSector.objects.all()[0]
        second = FakeSector.objects.exclude(title=first.title)[0]
        field = CreatorModelChoiceField(queryset=FakeSector.objects.filter(pk=first.pk))
        field.user = self.admin

        render_str = field.widget.render('sector', None)
        self.assertIn('---------', render_str)
        self.assertIn(first.title, render_str)
        self.assertNotIn(second.title, render_str)

    def test_queryset_property01(self):
        "No action."
        field = CreatorModelChoiceField(queryset=FakeSector.objects.none())

        self.assertHasNoAttr(field.widget, 'actions')
        self.assertListEqual([('', '---------')], [*field.widget.choices])

        field.queryset = FakeSector.objects.all()

        self.assertHasNoAttr(field.widget, 'actions')
        self.assertListEqual(
            [
                ('', '---------'),
                *((s.pk, str(s)) for s in FakeSector.objects.all()),
            ],
            [*field.choices],
        )

    def test_queryset_property02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=FakeSector.objects.none())
        field.user = self.admin

        sectors = [('', '---------')]
        self.assertListEqual(sectors, [*field.widget.choices])

        field.queryset = FakeSector.objects.all()
        sectors.extend((p.pk, str(p)) for p in FakeSector.objects.all())
        self.assertListEqual(sectors, [*field.widget.choices])

    def test_create_action_url(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.create_action_url = url = self.ADD_URL
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual((self.ADD_URL, True), field.creation_url_n_allowed)

    def test_render_url_n_allowed(self):
        widget = CreatorModelChoiceWidget(
            choices=[(1, 'A'), (2, 'B')],
            creation_url=self.ADD_URL,
            creation_allowed=True,
        )
        name = 'test'
        creation_label = _('Create')
        expected = '''
<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist"
    widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect"
                name="{name}" url="" widget="ui-creme-dselect">
            <option value="1" selected>A</option>
            <option value="2">B</option>
        </select>
    </li>
    <li>
        <button class="ui-creme-actionbutton with-icon" name="create" title="{create_label}"
                type="button" popupurl="{create_url}">
            {create_icon}<span>{create_label}</span>
        </button>
    </li>
</ul>'''.format(
            name=name,

            create_url=self.ADD_URL,
            create_label=creation_label,
            create_icon=self.get_icon(
                'add', size='form-widget', label=creation_label,
            ).render(),
        )
        self.maxDiff = None
        self.assertHTMLEqual(expected, widget.render(name, 1))
        self.assertHTMLEqual(expected, widget.render(name, 1, attrs={}))

    def test_render_url_n_allowed_disabled(self):
        widget = CreatorModelChoiceWidget(
            choices=[(1, 'A'), (2, 'B')],
            creation_url=self.ADD_URL,
            creation_allowed=True,
            attrs={'disabled': True},
        )
        name = 'testnoaction'
        self.assertHTMLEqual(
            f'<div class="select-wrapper">'
            f'  <select name="{name}" disabled>'
            f'    <option value="1" selected>A</option>'
            f'    <option value="2">B</option>'
            f'  </select>'
            f'  <div class="select-arrow">'
            f'</div>',
            widget.render(name, 1, attrs={'disabled': True}),
        )
        self.assertHTMLEqual(
            f'<div class="select-wrapper">'
            f'  <select name="{name}" disabled readonly>'
            f'    <option value="1" selected>A</option>'
            f'    <option value="2">B</option>'
            f'  </select>'
            f'  <div class="select-arrow">'
            f'</div>',
            widget.render(name, 1, attrs={'readonly': True}),
        )


class CreatorEnumerableModelChoiceFieldTestCase(_ConfigFieldTestCase):
    ADD_URL = reverse(
        'creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.create_admin()

    def test_ok(self):
        field = CreatorEnumerableModelChoiceField(model=FakeContact, field_name='sector')
        sector = FakeSector.objects.first()
        self.assertEqual(sector, field.clean(str(sector.id)))

    def test_empty_required(self):
        field = CreatorEnumerableModelChoiceField(model=FakeContact, field_name='sector')
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty_not_required(self):
        field = CreatorEnumerableModelChoiceField(
            model=FakeContact, field_name='sector', required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))

    def test_create_action_url(self):
        field = CreatorEnumerableModelChoiceField(model=FakeContact, field_name='sector')
        widget = field.widget

        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)
        self.assertIsNone(widget.create_url)

        field.create_action_url = url = self.ADD_URL
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)
        self.assertEqual(url, widget.create_url)

    def test_creation_url_n_allowed(self):
        field = CreatorEnumerableModelChoiceField(model=FakeContact, field_name='sector')

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual((self.ADD_URL, True), field.creation_url_n_allowed)

    def test_creation_not_allowed(self):
        field = CreatorEnumerableModelChoiceField(model=FakeContact, field_name='sector')
        user = self.create_user(
            index=1,
            role=self.create_role(
                name='Industry',
                allowed_apps=['persons'],  # Not admin
            ),
        )

        field.user = user
        self.assertTupleEqual((self.ADD_URL, False), field.creation_url_n_allowed)


class CreatorModelMultipleChoiceFieldTestCase(_ConfigFieldTestCase):
    ADD_URL = reverse(
        'creme_config__create_instance_from_widget',
        args=('creme_core', 'fake_sector'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.create_admin()

    def test_actions_not_admin(self):
        user = self.create_user(
            index=1, role=self.create_role(name='Not admin', allowed_apps=['creme_core']),
        )

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        self.assertEqual('', field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        label = str(FakeSector.creation_label)
        self.assertEqual(label, str(field.widget.creation_label))

        field.user = user

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(label, str(field.widget.creation_label))

        field.user = None

        self.assertEqual('', field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(label, str(field.widget.creation_label))

    def test_actions_admin(self):
        # admin = create_user()
        admin = self.admin

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(FakeSector.creation_label, field.widget.creation_label)

    def test_actions_admin_not_creatable(self):
        admin = self.admin

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = admin
        self.assertFalse(field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(FakePosition.creation_label, field.widget.creation_label)

    def test_actions_superuser(self):
        admin = self.admin

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = admin
        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(str(FakeSector.creation_label), field.widget.creation_label)

    def test_queryset_no_action(self):
        "No action."
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertListEqual(sectors, [*field.choices])

        render_str = field.widget.render('position', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_queryset(self):
        "With action."
        user = self.admin
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = user

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertListEqual(sectors, [*field.choices])

        render_str = field.widget.render('sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_filtered_queryset_no_action(self):
        "No action."
        first_sector = FakeSector.objects.first()
        field = CreatorModelMultipleChoiceField(
            queryset=FakeSector.objects.filter(pk=first_sector.pk),
        )

        positions = [(first_sector.pk, first_sector.title)]
        self.assertListEqual(positions, [*field.choices])

        render_str = field.widget.render('position', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_filtered_queryset(self):
        "With action."
        user = self.login_as_root_and_get()
        first_sector = FakeSector.objects.first()

        field = CreatorModelMultipleChoiceField(
            queryset=FakeSector.objects.filter(pk=first_sector.pk),
        )
        field.user = user

        positions = [(first_sector.pk, first_sector.title)]
        self.assertListEqual(positions, [*field.choices])

        render_str = field.widget.render('Sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_set_queryset_property_no_action(self):
        "No action."
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.none())

        self.assertHasNoAttr(field.widget, 'actions')
        self.assertListEqual([], [*field.widget.choices])

        render_str = field.widget.render('sector', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

        field.queryset = FakeSector.objects.all()

        positions = [(s.pk, str(s)) for s in FakeSector.objects.all()]
        self.assertListEqual(positions, [*field.choices])

        render_str = field.widget.render('sector', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_set_queryset_property(self):
        "With action."
        user = self.admin

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.none())
        field.user = user

        self.assertListEqual([], [*field.widget.choices])
        self.assertTrue(field.widget.creation_allowed)

        render_str = field.widget.render('position', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

        field.queryset = FakeSector.objects.all()

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertListEqual(sectors, [*field.choices])

        render_str = field.widget.render('sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_create_action_url(self):
        user = self.admin
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        url = '/other_url'
        field.create_action_url = url
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = user
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        user = self.admin
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = user
        self.assertTupleEqual((self.ADD_URL, True), field.creation_url_n_allowed)


class CustomMultiEnumChoiceFieldTestCase(_ConfigFieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.create_admin()

    @staticmethod
    def _build_url(cfield):
        return reverse('creme_config__add_custom_enum', args=(cfield.id,))

    def test_ok(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )
        cfeval01 = create_evalue(value='C')
        cfeval02 = create_evalue(value='Python')

        admin = self.admin

        field = CustomMultiEnumChoiceField(
            custom_field=cfield,
            user=admin,
            choices=[
                ('', '-------'),
                (cfeval01.id, cfeval01.value),
                (cfeval02.id, cfeval02.value),
            ],
            required=False,
        )
        self.assertEqual(cfield, field.custom_field)
        self.assertEqual(admin, field.user)

        url = self._build_url(cfield)

        widget = field.widget
        self.assertIs(widget.creation_allowed, True)
        self.assertEqual(url, widget.creation_url)

        expected_label = _('Create a choice')
        self.assertEqual(expected_label, widget.creation_label)

        name = f'cfield_{cfield.id}'
        render_str = field.widget.render(name, None)
        self.assertIn(url, render_str)
        self.assertIn(expected_label, render_str)

        str_id1 = str(cfeval01.id)
        str_id2 = str(cfeval02.id)
        self.assertListEqual([cfeval01.id], field.clean([str_id1]))
        self.assertListEqual([cfeval02.id], field.clean([str_id2]))
        self.assertListEqual(
            [cfeval01.id, cfeval02.id],
            field.clean([str_id1, str_id2])
        )
        self.assertListEqual([], field.clean(''))

    def test_user_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )
        field = CustomMultiEnumChoiceField(custom_field=cfield)
        self.assertIsNone(field.user)

        widget = field.widget
        self.assertIs(widget.creation_allowed, False)
        self.assertEqual('', widget.creation_url)
        self.assertEqual(_('Create a choice'), widget.creation_label)

        # ---
        field.user = self.admin
        self.assertTrue(widget.creation_allowed)
        self.assertEqual(self._build_url(cfield), widget.creation_url)

        # ---
        field.user = None
        self.assertFalse(widget.creation_allowed)

    def test_custom_field_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )
        field = CustomMultiEnumChoiceField(user=self.admin)
        self.assertIsNone(field.custom_field)

        widget = field.widget
        self.assertIs(widget.creation_allowed, False)
        self.assertEqual('', widget.creation_url)
        self.assertEqual(_('Create a choice'), widget.creation_label)

        # ---
        field.custom_field = cfield
        self.assertTrue(widget.creation_allowed)
        self.assertEqual(self._build_url(cfield), widget.creation_url)

        # ---
        field.custom_field = None
        self.assertFalse(widget.creation_allowed)

    def test_permission(self):
        user = self.create_user(
            index=1,
            role=self.create_role(name='Not admin', allowed_apps=['creme_core']),
        )
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )
        field = CustomMultiEnumChoiceField(custom_field=cfield, user=user)

        self.assertFalse(field.widget.creation_allowed)

    def test_create_action_url_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )
        field = CustomMultiEnumChoiceField(custom_field=cfield)

        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.create_action_url = url = f'this/is/an/url/{cfield.id}'
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomMultiEnumChoiceField(custom_field=cfield)

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = self.admin
        self.assertTupleEqual(
            (reverse('creme_config__add_custom_enum', args=(cfield.id,)), True),
            field.creation_url_n_allowed,
        )


class MenuEntriesFieldTestCase(_ConfigFieldTestCase):
    def test_creators(self):
        label = 'Create a separator'
        creator1 = MenuEntriesField.EntryCreator(
            label=label, entry_class=Separator1Entry,
        )
        self.assertEqual(label, creator1.label)
        self.assertEqual(Separator1Entry, creator1.entry_class)
        self.assertEqual(
            reverse('creme_config__add_menu_special_level1', args=(Separator1Entry.id,)),
            creator1.url,
        )

        # ---
        copied = copy(creator1)
        self.assertIsInstance(copied, MenuEntriesField.EntryCreator)
        self.assertEqual(label, copied.label)
        self.assertEqual(Separator1Entry, copied.entry_class)

        self.assertEqual(creator1, copied)
        self.assertNotEqual(
            creator1,
            MenuEntriesField.EntryCreator(
                label=f'not {label}', entry_class=Separator1Entry,
            )
        )
        self.assertNotEqual(
            creator1,
            MenuEntriesField.EntryCreator(
                label=label, entry_class=CustomURLEntry,
            )
        )

        # ---
        self.assertEqual(
            _('Add a separator'),
            MenuEntriesField.EntryCreator(Separator1Entry).label,
        )

    def test_attributes01(self):
        class EmptyLabelEntry(MenuEntry):  # Should be ignored
            id = 'creme_core-empty_label'
            model = FakeSector

        field = MenuEntriesField()
        self.assertIs(menu_registry, field.menu_registry)
        self.assertEqual(1, field.entry_level)
        self.assertListEqual([], [*field.excluded_entry_ids])

        creators = [
            MenuEntriesField.EntryCreator(entry_class=Separator1Entry),
            MenuEntriesField.EntryCreator(entry_class=CustomURLEntry),
        ]
        self.assertListEqual(creators, [*field.extra_entry_creators])

        widget = field.widget
        self.assertListEqual(creators, widget.extra_entry_creators)

        my_registry = MenuRegistry().register(
            ContainerEntry,
            FakeContactsEntry, FakeContactCreationEntry,
            FakeOrganisationsEntry, FakeOrganisationCreationEntry,
            EmptyLabelEntry,
        )
        field.menu_registry = my_registry
        self.assertIs(my_registry, field.menu_registry)

        excluded_entry_ids = (FakeContactsEntry.id, FakeContactCreationEntry.id)
        field.excluded_entry_ids = excluded_entry_ids
        self.assertListEqual([*excluded_entry_ids], [*field.excluded_entry_ids])

        choices = widget.regular_entry_choices
        self.assertIsInstance(choices, CallableChoiceIterator)

        choices_list = [*choices]
        self.assertInChoices(
            value=FakeOrganisationsEntry.id,
            label=FakeOrganisationsEntry().label,
            choices=choices_list,
        )
        self.assertInChoices(
            value=FakeOrganisationCreationEntry.id,
            label=FakeOrganisationCreationEntry().label,
            choices=choices_list,
        )
        self.assertNotInChoices(value=FakeContactsEntry.id, choices=choices_list)
        self.assertNotInChoices(value=ContainerEntry.id,    choices=choices_list)
        self.assertNotInChoices(value=EmptyLabelEntry.id,   choices=choices_list)

    def test_attributes02(self):
        my_registry = MenuRegistry().register(
            ContainerEntry, Separator1Entry,
            FakeContactsEntry, FakeContactCreationEntry,
            FakeOrganisationsEntry, FakeOrganisationCreationEntry,
        )
        creator = MenuEntriesField.EntryCreator(
            label='Add an entry separator',
            entry_class=Separator1Entry,
        )
        excluded_entry_ids = (FakeContactsEntry.id, FakeContactCreationEntry.id)
        field = MenuEntriesField(
            menu_registry=my_registry,
            entry_level=2,
            excluded_entry_ids=excluded_entry_ids,
            extra_entry_creators=[creator],
        )
        self.assertIs(my_registry, field.menu_registry)
        self.assertEqual(2, field.entry_level)
        self.assertListEqual([*excluded_entry_ids], [*field.excluded_entry_ids])
        self.assertListEqual([creator], [*field.extra_entry_creators])

    def test_regular_entry_choices(self):
        "Exclude creators."
        my_registry = MenuRegistry().register(
            ContainerEntry, Separator1Entry,
            FakeContactsEntry, FakeContactCreationEntry,
        )
        creator = MenuEntriesField.EntryCreator(
            label='Add an entry separator',
            entry_class=Separator1Entry,
        )
        field = MenuEntriesField(
            menu_registry=my_registry,
            excluded_entry_ids=[FakeContactCreationEntry.id],
            extra_entry_creators=[creator],
        )

        choices = [*field.widget.regular_entry_choices]
        self.assertInChoices(
            value=FakeContactsEntry.id,
            label=FakeContactsEntry().label,
            choices=choices,
        )
        self.assertNotInChoices(value=FakeContactCreationEntry.id, choices=choices)
        self.assertNotInChoices(value=FakeOrganisationsEntry.id,   choices=choices)
        self.assertNotInChoices(value=Separator1Entry.id,          choices=choices)

    def test_prepare_value(self):
        field = MenuEntriesField()
        self.assertJSONEqual('[]', field.prepare_value([]))

        invalid_data = InvalidJSONInput('[')
        self.assertEqual(invalid_data, field.prepare_value(invalid_data))

        label2 = 'Creation'
        entry_as_dicts = [
            {
                'label': str(FakeContactsEntry().label),
                'value': {'id': FakeContactsEntry.id},
            }, {
                'label': label2,
                'value': {'id': Separator1Entry.id, 'data': {'label': label2}},
            }, {
                'label': str(FakeContactCreationEntry().label),
                'value': {'id': FakeContactCreationEntry.id},
            },
        ]
        expected_json = json_dump(entry_as_dicts)
        self.assertJSONEqual(
            expected_json,
            field.prepare_value([d['value'] for d in entry_as_dicts]),
        )
        self.assertJSONEqual(
            expected_json,
            field.prepare_value([
                FakeContactsEntry(),
                Separator1Entry(data={'label': label2}),
                FakeContactCreationEntry(),
            ]),
        )

        self.assertJSONEqual(
            json_dump([
                {'no_id_key': 'whatever'},
                {'id': 'invalid_id'},
                {'id': [12]},
                [f'id="{Separator1Entry.id}"'],
                {'id': Separator1Entry.id, 'data': [1, 2]},
                {
                    'label': label2,
                    'value': {'id': Separator1Entry.id, 'data': {'label': label2}},
                },
            ]),
            field.prepare_value([
                {'no_id_key': 'whatever'},
                {'id': 'invalid_id'},
                {'id': [12]},
                [f'id="{Separator1Entry.id}"'],
                {'id': Separator1Entry.id, 'data': [1, 2]},
                {'id': Separator1Entry.id, 'data': {'label': label2}},
            ]),
        )

    def test_deepcopy(self):
        field1 = MenuEntriesField()
        field2 = deepcopy(field1)

        self.assertIsNot(
            field1.widget.regular_entry_choices,
            field2.widget.regular_entry_choices,
        )

    def test_ok01(self):
        field = MenuEntriesField(
            menu_registry=MenuRegistry().register(
                FakeContactsEntry, FakeContactCreationEntry,
            ),
        )
        cleaned = field.clean(json_dump([
            {'id': FakeContactCreationEntry.id},
            {'id': FakeContactsEntry.id},
        ]))
        self.assertIsList(cleaned, length=2)
        self.assertIsInstance(cleaned[0], FakeContactCreationEntry)
        self.assertIsInstance(cleaned[1], FakeContactsEntry)

    def test_ok02(self):
        "Special Entry with label."
        field = MenuEntriesField()
        label = 'My group'
        cleaned = field.clean(json_dump([
            {'id': Separator1Entry.id, 'data': {'label': label}},
        ]))
        self.assertIsList(cleaned, length=1)

        entry = cleaned[0]
        self.assertIsInstance(entry, Separator1Entry)
        self.assertEqual(label, entry.label)

    def test_ok03(self):
        "Entry with extra-data."
        field = MenuEntriesField()
        label = 'Wikipedia'
        url = 'http://www.wikipedia.org'
        cleaned = field.clean(json_dump([
            {'id': CustomURLEntry.id, 'data': {'label': label, 'url': url}},
        ]))
        self.assertIsList(cleaned, length=1)

        entry = cleaned[0]
        self.assertIsInstance(entry, CustomURLEntry)
        self.assertEqual(label, entry.label)
        self.assertEqual(url,   entry.url)

    def test_ok04(self):
        "Entry with extra-data (custom entry)."
        class TestEntryForm(MenuEntryForm):
            count = forms.IntegerField(label='Count')

        class TestEntry(MenuEntry):
            id = 'creme_core-test'
            form_class = TestEntryForm

            def __init__(this, **kwargs):
                super().__init__(**kwargs)
                this.count = this.data.get('count', 0)

        field = MenuEntriesField(
            menu_registry=MenuRegistry().register(TestEntry),
            excluded_entry_ids=[TestEntry.id],  # <== ignored
            extra_entry_creators=[
                MenuEntriesField.EntryCreator(
                    label='Add a test entry', entry_class=TestEntry,
                ),
            ],
        )
        count = 12
        label = f'Are Contacts more than {count}?'
        cleaned = field.clean(json_dump([
            {'id': TestEntry.id, 'data': {'label': label, 'count': count}},
        ]))
        self.assertIsList(cleaned, length=1)

        entry = cleaned[0]
        self.assertIsInstance(entry, TestEntry)
        self.assertEqual(label, entry.label)
        self.assertEqual(count, entry.count)

    def test_empty_not_required(self):
        field = MenuEntriesField(required=False)
        self.assertListEqual([], field.clean(''))
        self.assertListEqual([], field.clean('[]'))

    def test_empty_required(self):
        self.assertFormfieldError(
            field=MenuEntriesField(required=True),
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_invalid_JSON(self):
        self.assertFormfieldError(
            field=MenuEntriesField(),
            value='[',
            messages=_('Enter a valid JSON.'),
            codes='invalid',
        )

    def test_invalid_type(self):
        field = MenuEntriesField()
        msg = 'Enter a valid JSON list of dictionaries.'
        self.assertFormfieldError(
            field=field, value=json_dump({'data': 'foobar'}),
            messages=msg, codes='invalid_type',
        )
        self.assertFormfieldError(
            field=field, value=json_dump(['foo', 'bar']),
            messages=msg, codes='invalid_type',
        )
        # TODO: complete ??

    def test_invalid_data01(self):
        "Missing Id."
        self.assertFormfieldError(
            field=MenuEntriesField(),
            value=json_dump([{'notid': 'foobar'}]),
            messages=_('Enter a valid list of entries: %(error)s.') % {'error': _('no entry ID')},
            codes='invalid_data',
        )

    def test_invalid_data02(self):
        "Invalid label/extra-data."
        field = MenuEntriesField()
        label = 'Wikipedia'
        url = 'http://www.wikipedia.org'

        msg_fmt = _('Enter a valid list of entries: %(error)s.')
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': CustomURLEntry.id, 'data': 12}]),
            messages=msg_fmt % {'error': '"12" is not a dictionary'},
            codes='invalid_data',
        )

        fmt_err = _('the entry «{entry}» is invalid ({error})').format
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': CustomURLEntry.id, 'data': {'label': label}}]),
            messages=msg_fmt % {
                'error': fmt_err(
                    entry='Custom URL entry',
                    error='{} -> {}'.format(_('URL'), _('This field is required.')),
                ),
            },
            codes='invalid_data',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': CustomURLEntry.id, 'data': {'label': label, 'url': 123}}]),
            messages=msg_fmt % {
                'error': fmt_err(
                    entry='Custom URL entry',
                    error='{} -> {}'.format(_('URL'), _('Enter a valid URL.')),
                ),
            },
            codes='invalid_data',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': CustomURLEntry.id, 'data': {'url': url}}]),
            messages=msg_fmt % {
                'error': fmt_err(
                    entry='Custom URL entry',
                    error='{} -> {}'.format(_('Label'), _('This field is required.')),
                ),
            },
            codes='invalid_data',
        )

    def test_invalid_data03(self):
        "Invalid extra-data (custom entry)."
        class TestDataForm(CremeForm):
            count = forms.IntegerField(label='Count')

        class TestEntry(MenuEntry):
            id = 'creme_core-test'
            form_class = TestDataForm

            def __init__(this, data=None, **kwargs):
                super().__init__(**kwargs)
                this.count = 0 if not data else data.get('count', 0)

        self.assertFormfieldError(
            field=MenuEntriesField(menu_registry=MenuRegistry().register(TestEntry)),
            value=json_dump([{
                'id': TestEntry.id,
                'label': 'Are Contacts more than 12?',
                'data': {'count': 'abc'},
            }]),
            messages=_('Enter a valid list of entries: %(error)s.') % {
                'error': _('the entry «{entry}» is invalid ({error})').format(
                    entry='TestEntry',
                    error='{} -> {}'.format('Count', _('Enter a whole number.')),
                ),
            },
            codes='invalid_data',
        )

    def test_invalid_entry_id01(self):
        "Not registered class."
        field = MenuEntriesField(
            menu_registry=MenuRegistry().register(FakeContactsEntry),
        )
        entry_id = FakeContactCreationEntry.id
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': entry_id}]),
            messages=_('Enter a valid list of entries: %(error)s.') % {
                'error': _('the entry ID "{}" is invalid.').format(entry_id),
            },
            codes='invalid_data',
        )

    def test_invalid_entry_id02(self):
        "Excluded class."
        field = MenuEntriesField(
            menu_registry=MenuRegistry().register(
                FakeContactsEntry, FakeContactCreationEntry,
            ),
            excluded_entry_ids=[FakeContactCreationEntry.id],
        )
        entry_id = FakeContactCreationEntry.id
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': entry_id}]),
            messages=_('Enter a valid list of entries: %(error)s.') % {
                'error': _('the entry ID "{}" is invalid.').format(entry_id),
            },
            codes='invalid_data',
        )

    def test_invalid_entry_id03(self):
        "Not registered extra class."
        field = MenuEntriesField(
            menu_registry=MenuRegistry().register(FakeContactsEntry),
        )
        entry_id = CustomURLEntry.id
        self.assertFormfieldError(
            field=field,
            value=json_dump([{
                'id': entry_id,
                'label': 'My label', 'data': {'url': 'https://whateve.r'}
            }]),
            messages=_('Enter a valid list of entries: %(error)s.') % {
                'error': _('the entry ID "{}" is invalid.').format(entry_id),
            },
            codes='invalid_data',
        )

    def test_invalid_entry_id04(self):
        "Invalid level."
        field = MenuEntriesField()

        entry_id = ContainerEntry.id
        self.assertIsNotNone(field.menu_registry.get_class(entry_id))
        self.assertFormfieldError(
            field=field,
            value=json_dump([{'id': entry_id}]),
            messages=_('Enter a valid list of entries: %(error)s.') % {
                'error': _('the entry ID "{}" is invalid.').format(entry_id),
            },
            codes='invalid_data',
        )


class BricksConfigFieldTestCase(_ConfigFieldTestCase):
    choices = ((1, 'a'), (2, 'b'), (3, 'c'), (4, 'd'))

    def test_initial(self):
        field = BricksConfigField()
        self.assertEqual(field.initial, {'top': [], 'left': [], 'right': [], 'bottom': []})

        field = BricksConfigField(initial={'top': [], 'left': []})
        self.assertEqual(field.initial, {'top': [], 'left': []})

    def test_required(self):
        self.assertRaises(NotImplementedError, BricksConfigField, required=False)

    def test_choices(self):
        field = BricksConfigField(choices=self.choices)

        choices_list = [*self.choices]
        self.assertListEqual(field.choices, choices_list)
        self.assertListEqual(field._choices, choices_list)
        self.assertListEqual(field.widget.choices, choices_list)

        choices_set = {1, 2, 3, 4}
        self.assertEqual(field._valid_choices, choices_set)

    def test_copyfield(self):
        field = BricksConfigField(choices=self.choices)
        field_copy = deepcopy(field)
        self.assertIsNot(field._choices, field_copy._choices)
        self.assertIsNot(field._valid_choices, field_copy._valid_choices)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=BricksConfigField(choices=self.choices),
            value='TEST',
            messages=_('Enter a valid JSON.'),
            codes='invalid',
        )

    @parameterized.expand([
        [""], [None],
    ])
    def test_clean_required(self, value):
        self.assertFormfieldError(
            field=BricksConfigField(choices=self.choices),
            value=value,
            messages=_('Your configuration is empty!'),
            codes='required',
        )

    @parameterized.expand([
        ["42"],
        [json_dump("not a dict")],
        [json_dump(["not a dict"])],
        [json_dump({"top": "lot a list"})],
    ])
    def test_clean_invalid_not_a_dict_of_lists(self, value):
        self.assertFormfieldError(
            field=BricksConfigField(choices=self.choices),
            value=value,
            messages=_("The value doesn't match the expected format."),
            codes='invalid_format',
        )

    def test_clean_invalid_choices(self):
        error_fmt = _('Select a valid choice. %(value)s is not one of the available choices.')
        self.assertFormfieldError(
            field=BricksConfigField(choices=self.choices),
            value=json_dump({'top': [5], 'left': [6]}),
            messages=[error_fmt % {'value': 5}, error_fmt % {'value': 6}],
            codes=['invalid_choice'] * 2,
        )

    def test_clean_duplicates(self):
        class TestBrick:
            def __init__(self, verbose_name):
                self.verbose_name = verbose_name

        error_fmt = _('The following block should be displayed only once: «%(block)s»')
        self.assertFormfieldError(
            field=BricksConfigField(
                choices=[
                    (1, TestBrick('a')), (2, TestBrick('b')),
                    (3, TestBrick('c')), (4, TestBrick('d')),
                ],
            ),
            value=json_dump({'top': [1, 2], 'left': [2, 3], 'bottom': [3, 4]}),
            messages=[error_fmt % {'block': 'b'}, error_fmt % {'block': 'c'}],
            codes=['duplicated_brick'] * 2,
        )

    def test_clean_empty_config(self):
        self.assertFormfieldError(
            field=BricksConfigField(choices=self.choices),
            value=json_dump({'top': [], 'left': []}),
            messages=_('Your configuration is empty!'),
            codes='required',
        )

    def test_clean_ok(self):
        field = BricksConfigField(choices=self.choices)
        self.assertDictEqual(
            {'top': [1], 'left': [2, 3], 'right': [], 'bottom': []},
            field.clean(json_dump({'top': [1], 'left': [2, 3]})),
        )
