# -*- coding: utf-8 -*-

try:
    from django.contrib.auth import get_user_model
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import UserRole
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakePosition

#    from creme.persons.models import Position

    from ..forms.fields import CreatorModelChoiceField, CreatorModelMultipleChoiceField
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CreatorModelChoiceFieldTestCase(CremeTestCase):
    # ADD_URL = '/creme_config/creme_core/fake_position/add_widget/'
    ADD_URL = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_position'))

    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     # cls.populate('creme_core', 'persons')
    #     cls.populate('creme_core')

    def _create_superuser(self):
        return get_user_model().objects.create_superuser(username='averagejoe',
                                                         first_name='Joe',
                                                         last_name='Average',
                                                         email='averagejoe@company.com',
                                                        )

    def test_actions_not_admin(self):
        with self.assertNumQueries(0):
            field = CreatorModelChoiceField(queryset=FakePosition.objects.all())

#        self.assertFalse(hasattr(field.widget, 'actions'))

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']  # Not admin
        role.save()

        user = get_user_model().objects.create_user(username='averagejoe',
                                                    first_name='Joe',
                                                    last_name='Average',
                                                    email='averagejoe@company.com',
                                                   )
        user.role = role

        field.user = user
#        self.assertEqual([('create', _(u'Add'), False,
#                           {'title': _(u"Can't add"),
# #                            'url':   '/creme_config/persons/position/add_widget/',
#                            'url':   self.ADD_URL,
#                           }
#                          )
#                         ],
#                         field.widget.actions
#                        )
        render_str = field.widget.render('position', None)
        self.assertIn(_(u'Cannot create'), render_str)

        field.user = None
#        self.assertFalse(hasattr(field.widget, 'actions'))
        render_str = field.widget.render('position', None)
        self.assertNotIn(_(u'Cannot create'), render_str)

    def test_actions_admin(self):
        field = CreatorModelChoiceField(queryset=FakePosition.objects.all())
#        self.assertFalse(hasattr(field.widget, 'actions'))

        role = UserRole(name='CEO')
#        role.admin_4_apps = ['persons']
        role.admin_4_apps = ['creme_core']
        role.save()

        admin = get_user_model().objects.create(username='chloe', role=role)
        admin.role = role

        field.user = admin
#        self.assertEqual([('create', _(u'Add'), True,
#                           {'title': _(u'Add'),
##                            'url':   '/creme_config/persons/position/add_widget/',
#                            'url':   self.ADD_URL,
#                           },
#                          )
#                         ],
#                         field.widget.actions
#                        )

        render_str = field.widget.render('position', None)
        self.assertIn(self.ADD_URL, render_str)
        self.assertIn(_(u'Create'), render_str)

        field.user = None
        # self.assertFalse(hasattr(field.widget, 'actions'))
        render_str = field.widget.render('position', None)
        self.assertNotIn(self.ADD_URL, render_str)

    def test_queryset01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=FakePosition.objects.all())
        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in FakePosition.objects.all())

        with self.assertNoException():
            choices = list(field.choices)

        self.assertEqual(positions, choices)

    def test_queryset02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=FakePosition.objects.all())
        field.user = self._create_superuser()

        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in FakePosition.objects.all())

        with self.assertNoException():
#            options = field.widget.delegate._get_options()
            options = list(field.choices)

        self.assertEqual(positions, options)

        # ------
        render_str = field.widget.render('position', None)
        self.assertIn(u'---------', render_str)

        for p in FakePosition.objects.all():
            self.assertIn(unicode(p), render_str)

    def test_filtered_queryset01(self):
        "No action"
        pk = FakePosition.objects.first().pk
        field = CreatorModelChoiceField(queryset=FakePosition.objects.filter(pk=pk))

        with self.assertNoException():
            choices = list(field.choices)

        self.assertEqual([(u'', u'---------'),
                          (pk, FakePosition.objects.get(pk=pk).title),
                         ],
                         choices
                        )

    def test_filtered_queryset02(self):
        "With action"
#        pk = Position.objects.first().pk
        first = FakePosition.objects.all()[0]
        second = FakePosition.objects.exclude(title=first.title)[0]
#        field = CreatorModelChoiceField(queryset=Position.objects.filter(pk=pk))
        field = CreatorModelChoiceField(queryset=FakePosition.objects.filter(pk=first.pk))
        field.user = self._create_superuser()

#        with self.assertNoException():
#            options = field.widget.delegate._get_options()
#
#        self.assertEqual([(u'', u'---------'),
#                          (pk, Position.objects.get(pk=pk).title),
#                         ],
#                         options
#                        )
        render_str = field.widget.render('position', None)
        self.assertIn(u'---------', render_str)
        self.assertIn(first.title, render_str)
        self.assertNotIn(second.title, render_str)

    def test_queryset_property01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=FakePosition.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual([(u'', u'---------')], list(field.widget.choices))

        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in FakePosition.objects.all())

        field.queryset = FakePosition.objects.all()

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual(positions, list(field.choices))

    def test_queryset_property02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=FakePosition.objects.none())
        field.user = self._create_superuser()

        positions = [(u'', u'---------')]
#        self.assertEqual([(u'', u'---------')], field.widget.delegate._get_options())
        self.assertEqual(positions, list(field.widget.choices))

        field.queryset = FakePosition.objects.all()
#        self.assertEqual(positions, field.widget.delegate._get_options())
        positions.extend((p.pk, unicode(p)) for p in FakePosition.objects.all())
        self.assertEqual(positions, list(field.widget.choices))

    def test_create_action_url(self):
        field = CreatorModelChoiceField(FakePosition.objects.all())

#        self.assertIsNone(field.create_action_url)
        self.assertEqual('', field.create_action_url)
        self.assertEqual(('', False), field.creation_url_n_allowed)
#        self.assertEqual('/creme_config/persons/position/add_widget/',
#                         field._build_create_action_url('persons', 'position')
#                        )

        field.create_action_url = url = self.ADD_URL
        self.assertEqual((url, False), field.creation_url_n_allowed)

        field.user = self._create_superuser()
        self.assertEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        field = CreatorModelChoiceField(FakePosition.objects.all())

        self.assertEqual(('', False), field.creation_url_n_allowed)

        field.user = self._create_superuser()
        self.assertEqual((self.ADD_URL, True), field.creation_url_n_allowed)


class CreatorModelMultipleChoiceFieldTestCase(CremeTestCase):
    ADD_URL = reverse('creme_config__create_instance_from_widget', args=('creme_core', 'fake_position'))

    def test_actions_not_admin(self):
        user = self.login(is_superuser=False, allowed_apps=('persons',))

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())

        self.assertEqual('', field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(_(u'Create'), unicode(field.widget.creation_label))

        field.user = user

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(_(u"Create"), unicode(field.widget.creation_label))

        field.user = None

        self.assertEqual('', field.widget.creation_url)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(_(u"Create"), unicode(field.widget.creation_label))

    def test_actions_admin(self):
        admin = self.login(is_superuser=False, admin_4_apps=('creme_core',))

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(FakePosition.creation_label, field.widget.creation_label)

    def test_actions_superuser(self):
        admin = self.login()

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = admin

        self.assertEqual(self.ADD_URL, field.widget.creation_url)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(FakePosition.creation_label, field.widget.creation_label)

    def test_queryset_no_action(self):
        "No action"
        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())

        positions = [(p.pk, unicode(p)) for p in FakePosition.objects.all()]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(unicode(FakePosition.creation_label), render_str)

    def test_queryset(self):
        "With action"
        user = self.login()
        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.all())
        field.user = user

        positions = [(p.pk, unicode(p)) for p in FakePosition.objects.all()]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertIn(unicode(FakePosition.creation_label), render_str)

    def test_filtered_queryset_no_action(self):
        "No action"
        first_position = FakePosition.objects.first()
        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.filter(pk=first_position.pk))

        positions = [(first_position.pk, first_position.title)]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(unicode(FakePosition.creation_label), render_str)

    def test_filtered_queryset(self):
        "With action"
        user = self.login()
        first_position = FakePosition.objects.first()

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.filter(pk=first_position.pk))
        field.user = user

        positions = [(first_position.pk, first_position.title)]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertIn(unicode(FakePosition.creation_label), render_str)

    def test_set_queryset_property_no_action(self):
        "No action"
        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual([], list(field.widget.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(unicode(FakePosition.creation_label), render_str)

        field.queryset = FakePosition.objects.all()

        positions = [(p.pk, unicode(p)) for p in FakePosition.objects.all()]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertNotIn(unicode(FakePosition.creation_label), render_str)

    def test_set_queryset_property(self):
        "With action"
        user = self.login()

        field = CreatorModelMultipleChoiceField(queryset=FakePosition.objects.none())
        field.user = user

        self.assertEqual([], list(field.widget.choices))
        self.assertTrue(field.widget.creation_allowed)

        render_str = field.widget.render('position', None)
        self.assertIn(unicode(FakePosition.creation_label), render_str)

        field.queryset = FakePosition.objects.all()

        positions = [(p.pk, unicode(p)) for p in FakePosition.objects.all()]
        self.assertEqual(positions, list(field.choices))

        render_str = field.widget.render('position', None)
        self.assertIn(unicode(FakePosition.creation_label), render_str)

    def test_create_action_url(self):
        user = self.login()
        field = CreatorModelMultipleChoiceField(FakePosition.objects.all())

#        self.assertIsNone(field.create_action_url)
        self.assertEqual('', field.create_action_url)
        self.assertEqual(('', False), field.creation_url_n_allowed)
#        self.assertEqual('/creme_config/persons/position/add_widget/',
#                         field._build_create_action_url('persons', 'position')
#                        )

        url = '/other_url'
        field.create_action_url = url
        self.assertEqual((url, False), field.creation_url_n_allowed)

        field.user = user
        self.assertEqual((url, True), field.creation_url_n_allowed)

    def test_creation_url_n_allowed(self):
        user = self.login()
        field = CreatorModelMultipleChoiceField(FakePosition.objects.all())

        self.assertEqual(('', False), field.creation_url_n_allowed)

        field.user = user
        self.assertEqual((self.ADD_URL, True), field.creation_url_n_allowed)
