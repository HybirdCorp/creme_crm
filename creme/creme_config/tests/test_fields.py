# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CustomField,
    CustomFieldEnumValue,
    FakeContact,
    FakePosition,
    FakeSector,
    UserRole,
)
from creme.creme_core.tests.base import CremeTestCase

from ..forms.fields import (
    CreatorModelChoiceField,
    CreatorModelMultipleChoiceField,
    CustomEnumChoiceField,
    CustomMultiEnumChoiceField,
)
from ..forms.widgets import CreatorModelChoiceWidget


def create_user(admin=True):
    role = UserRole(name='Average')
    if admin:
        role.admin_4_apps = ['creme_core']
    else:
        role.allowed_apps = ['creme_core']

    role.save()

    return get_user_model().objects.create(
        username='averagejoe',
        first_name='Joe',
        last_name='Average',
        email='averagejoe@company.com',
        role=role,
    )


class CreatorModelChoiceFieldTestCase(CremeTestCase):
    ADD_URL = reverse(
        'creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'),
    )

    def test_actions_not_admin(self):
        with self.assertNumQueries(0):
            field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        role = UserRole(name='Industry')
        role.allowed_apps = ['persons']  # Not admin
        role.save()

        user = get_user_model().objects.create_user(
            username='averagejoe',
            first_name='Joe',
            last_name='Average',
            email='averagejoe@company.com',
        )
        user.role = role

        field.user = user

        render_str = field.widget.render('sector', None)
        self.assertIn(_('Cannot create'), render_str)

        field.user = None
        render_str = field.widget.render('sector', None)
        self.assertNotIn(_('Cannot create'), render_str)

    def test_actions_admin(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        role = UserRole(name='CEO')
        role.admin_4_apps = ['creme_core']
        role.save()

        field.user = get_user_model().objects.create(username='chloe', role=role)

        render_str = field.widget.render('sector', None)
        self.assertIn(self.ADD_URL, render_str)
        self.assertIn(str(FakeSector.creation_label), render_str)

        field.user = None
        render_str = field.widget.render('sector', None)
        self.assertNotIn(self.ADD_URL, render_str)

    def test_actions_admin_no_creatable(self):
        field = CreatorModelChoiceField(queryset=FakePosition.objects.all())

        role = UserRole(name='CEO')
        role.admin_4_apps = ['creme_core']
        role.save()

        field.user = get_user_model().objects.create(username='chloe', role=role)

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
        field.user = create_user()

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
        "No action"
        pk = FakeSector.objects.first().pk
        field = CreatorModelChoiceField(queryset=FakeSector.objects.filter(pk=pk))

        with self.assertNoException():
            choices = [*field.choices]

        self.assertListEqual(
            [
                ('', '---------'),
                (pk, FakeSector.objects.get(pk=pk).title),
            ],
            choices
        )

    def test_filtered_queryset02(self):
        "With action"
        first = FakeSector.objects.all()[0]
        second = FakeSector.objects.exclude(title=first.title)[0]
        field = CreatorModelChoiceField(queryset=FakeSector.objects.filter(pk=first.pk))
        # field.user = self._create_superuser()
        field.user = create_user()

        render_str = field.widget.render('sector', None)
        self.assertIn('---------', render_str)
        self.assertIn(first.title, render_str)
        self.assertNotIn(second.title, render_str)

    def test_queryset_property01(self):
        "No action."
        field = CreatorModelChoiceField(queryset=FakeSector.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertListEqual([('', '---------')], [*field.widget.choices])

        field.queryset = FakeSector.objects.all()

        self.assertFalse(hasattr(field.widget, 'actions'))
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
        # field.user = self._create_superuser()
        field.user = create_user()

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

        field.user = create_user()
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = create_user()
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
            {create_icon}{create_label}
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
            '<select name="{name}" disabled>'
            '  <option value="1" selected>A</option>'
            '  <option value="2">B</option>'
            '</select>'.format(name=name),
            widget.render(name, 1, attrs={'disabled': True}),
        )
        self.assertHTMLEqual(
            '<select name="{name}" disabled readonly>'
            '  <option value="1" selected>A</option>'
            '  <option value="2">B</option>'
            '</select>'.format(name=name),
            widget.render(name, 1, attrs={'readonly': True}),
        )


class CreatorModelMultipleChoiceFieldTestCase(CremeTestCase):
    ADD_URL = reverse(
        'creme_config__create_instance_from_widget',
        args=('creme_core', 'fake_sector'),
    )

    def test_actions_not_admin(self):
        user = create_user(admin=False)

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
        admin = create_user()

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(FakeSector.creation_label, field.widget.creation_label)

    def test_actions_admin_not_creatable(self):
        admin = create_user()

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = admin

        self.assertFalse(field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(FakePosition.creation_label, field.widget.creation_label)

    def test_actions_superuser(self):
        admin = create_user()

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
        user = create_user()
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
        user = self.login()
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

        self.assertFalse(hasattr(field.widget, 'actions'))
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
        # user = self.login()
        user = create_user()

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
        # user = self.login()
        user = create_user()
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        url = '/other_url'
        field.create_action_url = url
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = user
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        user = create_user()
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = user
        self.assertTupleEqual((self.ADD_URL, True), field.creation_url_n_allowed)


class CustomEnumChoiceFieldTestCase(CremeTestCase):
    @staticmethod
    def _build_url(cfield):
        return reverse('creme_config__add_custom_enum', args=(cfield.id,))

    def test_ok(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        cfeval01  = create_evalue(value='C')
        cfeval02 = create_evalue(value='Python')

        admin = create_user()

        field = CustomEnumChoiceField(
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

        self.assertEqual(cfeval01.id, field.clean(str(cfeval01.id)))
        self.assertEqual(cfeval02.id, field.clean(str(cfeval02.id)))
        self.assertEqual('',          field.clean(''))

    def test_user_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomEnumChoiceField(custom_field=cfield)
        self.assertIsNone(field.user)

        widget = field.widget
        self.assertIs(widget.creation_allowed, False)
        self.assertEqual('', widget.creation_url)
        self.assertEqual(_('Create a choice'), widget.creation_label)

        # ---
        field.user = create_user()
        self.assertTrue(widget.creation_allowed)
        self.assertEqual(self._build_url(cfield), widget.creation_url)

        # ---
        field.user = None
        self.assertFalse(widget.creation_allowed)

    def test_custom_field_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomEnumChoiceField(user=create_user())
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
        user = create_user(admin=False)
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomEnumChoiceField(custom_field=cfield, user=user)

        self.assertFalse(field.widget.creation_allowed)

    def test_create_action_url_property(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomEnumChoiceField(custom_field=cfield)

        self.assertEqual('', field.create_action_url)
        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.create_action_url = url = f'this/is/an/url/{cfield.id}'
        self.assertTupleEqual((url, False), field.creation_url_n_allowed)

        field.user = create_user()
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomEnumChoiceField(custom_field=cfield)

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = create_user()
        self.assertTupleEqual(
            (reverse('creme_config__add_custom_enum', args=(cfield.id,)), True),
            field.creation_url_n_allowed
        )


class CustomMultiEnumChoiceFieldTestCase(CremeTestCase):
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

        admin = create_user()

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
        field.user = create_user()
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
        field = CustomMultiEnumChoiceField(user=create_user())
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
        user = create_user(admin=False)
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

        field.user = create_user()
        self.assertTupleEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        cfield = CustomField.objects.create(
            name='Programming languages',
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        field = CustomMultiEnumChoiceField(custom_field=cfield)

        self.assertTupleEqual(('', False), field.creation_url_n_allowed)

        field.user = create_user()
        self.assertTupleEqual(
            (reverse('creme_config__add_custom_enum', args=(cfield.id,)), True),
            field.creation_url_n_allowed,
        )
