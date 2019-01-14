# -*- coding: utf-8 -*-

try:
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import UserRole
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakePosition, FakeSector

    from ..forms.fields import CreatorModelChoiceField, CreatorModelMultipleChoiceField
    from ..forms.widgets import CreatorModelChoiceWidget
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CreatorModelChoiceFieldTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'))

    def _create_superuser(self):
        return get_user_model().objects.create_superuser(username='averagejoe',
                                                         first_name='Joe',
                                                         last_name='Average',
                                                         email='averagejoe@company.com',
                                                        )

    def test_actions_not_admin(self):
        with self.assertNumQueries(0):
            field = CreatorModelChoiceField(queryset=FakeSector.objects.all())

        role = UserRole(name='Industry')
        role.allowed_apps = ['persons']  # Not admin
        role.save()

        user = get_user_model().objects.create_user(username='averagejoe',
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

        admin = get_user_model().objects.create(username='chloe', role=role)
        admin.role = role

        field.user = admin

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

        admin = get_user_model().objects.create(username='chloe', role=role)
        admin.role = role

        field.user = admin

        render_str = field.widget.render('position', None)
        self.assertNotIn(reverse('creme_config__create_instance_from_widget',
                                 args=('creme_core', 'fake_position')
                                ),
                         render_str,
                        )
        self.assertNotIn(str(FakePosition.creation_label), render_str)

    def test_queryset01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        sectors = [('', '---------')]
        sectors.extend((p.pk, str(p)) for p in FakeSector.objects.all())

        with self.assertNoException():
            choices = list(field.choices)

        self.assertEqual(sectors, choices)

    def test_queryset02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=FakeSector.objects.all())
        field.user = self._create_superuser()

        sectors = [('', '---------')]
        sectors.extend((p.pk, str(p)) for p in FakeSector.objects.all())

        with self.assertNoException():
            options = list(field.choices)

        self.assertEqual(sectors, options)

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
            choices = list(field.choices)

        self.assertEqual([('', '---------'),
                          (pk, FakeSector.objects.get(pk=pk).title),
                         ],
                         choices
                        )

    def test_filtered_queryset02(self):
        "With action"
        first = FakeSector.objects.all()[0]
        second = FakeSector.objects.exclude(title=first.title)[0]
        field = CreatorModelChoiceField(queryset=FakeSector.objects.filter(pk=first.pk))
        field.user = self._create_superuser()

        render_str = field.widget.render('sector', None)
        self.assertIn('---------', render_str)
        self.assertIn(first.title, render_str)
        self.assertNotIn(second.title, render_str)

    def test_queryset_property01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=FakeSector.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual([('', '---------')], list(field.widget.choices))

        positions = [('', '---------')]
        positions.extend((s.pk, str(s)) for s in FakeSector.objects.all())

        field.queryset = FakeSector.objects.all()

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual(positions, list(field.choices))

    def test_queryset_property02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=FakeSector.objects.none())
        field.user = self._create_superuser()

        sectors = [('', '---------')]
        self.assertEqual(sectors, list(field.widget.choices))

        field.queryset = FakeSector.objects.all()
        sectors.extend((p.pk, str(p)) for p in FakeSector.objects.all())
        self.assertEqual(sectors, list(field.widget.choices))

    def test_create_action_url(self):
        field = CreatorModelChoiceField(FakeSector.objects.all())

        self.assertEqual('', field.create_action_url)
        self.assertEqual(('', False), field.creation_url_n_allowed)

        field.create_action_url = url = self.ADD_URL
        self.assertEqual((url, False), field.creation_url_n_allowed)

        field.user = self._create_superuser()
        self.assertEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        field = CreatorModelChoiceField(FakeSector.objects.all())

        self.assertEqual(('', False), field.creation_url_n_allowed)

        field.user = self._create_superuser()
        self.assertEqual((self.ADD_URL, True), field.creation_url_n_allowed)

    def test_render_url_n_allowed(self):
        widget = CreatorModelChoiceWidget(choices=[(1, 'A'), (2, 'B')],
                                          creation_url=self.ADD_URL,
                                          creation_allowed=True,
                                         )
        name = 'test'
        expected = \
'''<ul class="ui-layout hbox ui-creme-widget widget-auto ui-creme-actionbuttonlist"
        widget="ui-creme-actionbuttonlist">
    <li class="delegate">
        <select class="ui-creme-input ui-creme-widget widget-auto ui-creme-dselect" name="{name}" url=""
                widget="ui-creme-dselect">
            <option value="1" selected>A</option>
            <option value="2">B</option>
        </select>
    </li>
    <li>
        <button class="ui-creme-actionbutton" name="create" title="{create_label}"
                type="button" popupurl="{create_url}">{create_label}</button>
    </li>
</ul>'''.format(create_url=self.ADD_URL,
                create_label=_('Create'),
                name=name,
               )

        self.assertHTMLEqual(expected, widget.render(name, 1))
        self.assertHTMLEqual(expected, widget.render(name, 1, attrs={}))

    def test_render_url_n_allowed_disabled(self):
        widget = CreatorModelChoiceWidget(choices=[(1, 'A'), (2, 'B')],
                                          creation_url=self.ADD_URL,
                                          creation_allowed=True,
                                          attrs=dict(disabled=True)
                                         )
        name = 'testnoaction'

        self.assertHTMLEqual(
'''<select name="{name}" disabled>
    <option value="1" selected>A</option>
    <option value="2">B</option>
</select>'''.format(name=name),
            widget.render(name, 1, attrs={'disabled': True})
        )
        self.assertHTMLEqual(
'''<select name="{name}" disabled readonly>
    <option value="1" selected>A</option>
    <option value="2">B</option>
</select>'''.format(name=name),
            widget.render(name, 1, attrs={'readonly': True})
        )


class CreatorModelMultipleChoiceFieldTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_sector'))

    def test_actions_not_admin(self):
        user = self.login(is_superuser=False, allowed_apps=('persons',))

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
        admin = self.login(is_superuser=False, admin_4_apps=('creme_core',))

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(FakeSector.creation_label, field.widget.creation_label)

    def test_actions_admin_not_creatable(self):
        admin = self.login(is_superuser=False, admin_4_apps=('creme_core',))

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = admin

        self.assertFalse(field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(FakePosition.creation_label, field.widget.creation_label)

    def test_actions_superuser(self):
        admin = self.login()

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(str(FakeSector.creation_label), field.widget.creation_label)

    def test_queryset_no_action(self):
        "No action"
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertEqual(sectors, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_queryset(self):
        "With action"
        user = self.login()
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.all())
        field.user = user

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertEqual(sectors, list(field.choices))

        render_str = field.widget.render('sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_filtered_queryset_no_action(self):
        "No action"
        first_sector = FakeSector.objects.first()
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.filter(pk=first_sector.pk))

        positions = [(first_sector.pk, first_sector.title)]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_filtered_queryset(self):
        "With action"
        user = self.login()
        first_sector = FakeSector.objects.first()

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.filter(pk=first_sector.pk))
        field.user = user

        positions = [(first_sector.pk, first_sector.title)]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('Sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_set_queryset_property_no_action(self):
        "No action"
        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual([], list(field.widget.choices))

        render_str = field.widget.render('sector', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

        field.queryset = FakeSector.objects.all()

        positions = [(s.pk, str(s)) for s in FakeSector.objects.all()]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('sector', None)
        self.assertNotIn(str(FakeSector.creation_label), render_str)

    def test_set_queryset_property(self):
        "With action"
        user = self.login()

        field = CreatorModelMultipleChoiceField(queryset=FakeSector.objects.none())
        field.user = user

        self.assertEqual([], list(field.widget.choices))
        self.assertTrue(field.widget.creation_allowed)

        render_str = field.widget.render('position', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

        field.queryset = FakeSector.objects.all()

        sectors = [(p.pk, str(p)) for p in FakeSector.objects.all()]
        self.assertEqual(sectors, list(field.choices))

        render_str = field.widget.render('sector', None)
        self.assertIn(str(FakeSector.creation_label), render_str)

    def test_create_action_url(self):
        user = self.login()
        field = CreatorModelMultipleChoiceField(FakeSector.objects.all())

        self.assertEqual('', field.create_action_url)
        self.assertEqual(('', False), field.creation_url_n_allowed)

        url = '/other_url'
        field.create_action_url = url
        self.assertEqual((url, False), field.creation_url_n_allowed)

        field.user = user
        self.assertEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        user = self.login()
        field = CreatorModelMultipleChoiceField(FakeSector.objects.all())

        self.assertEqual(('', False), field.creation_url_n_allowed)

        field.user = user
        self.assertEqual((self.ADD_URL, True), field.creation_url_n_allowed)
