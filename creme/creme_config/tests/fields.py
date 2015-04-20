# -*- coding: utf-8 -*-

try:
    from django.contrib.auth import get_user_model
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import UserRole
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakePosition as Position

    #from creme.persons.models import Position

    from ..forms.fields import CreatorModelChoiceField
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('CreatorModelChoiceFieldTestCase', )


class CreatorModelChoiceFieldTestCase(CremeTestCase):
    ADD_URL = '/creme_config/creme_core/fake_position/add_widget/'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
#        cls.populate('creme_core', 'persons')
        cls.populate('creme_core')
        #cls.autodiscover()

    def _create_superuser(self):
        return get_user_model().objects.create_superuser(username='averagejoe',
                                                         first_name='Joe',
                                                         last_name='Average',
                                                         email='averagejoe@company.com',
                                                        )

    def test_actions_not_admin(self):
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        self.assertFalse(hasattr(field.widget, 'actions'))

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons'] #not admin
        role.save()

        user = get_user_model().objects.create_user(username='averagejoe',
                                                    first_name='Joe',
                                                    last_name='Average',
                                                    email='averagejoe@company.com',
                                                  )
        user.role = role

        field.user = user
        self.assertEqual([('create', _(u'Add'), False,
                           {'title': _(u"Can't add"),
#                            'url':   '/creme_config/persons/position/add_widget/',
                            'url':   self.ADD_URL,
                           }
                          )
                         ],
                         field.widget.actions
                        )

        field.user = None
        self.assertFalse(hasattr(field.widget, 'actions'))

    def test_actions_admin(self):
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        self.assertFalse(hasattr(field.widget, 'actions'))

        role = UserRole(name='CEO')
#        role.admin_4_apps = ['persons']
        role.admin_4_apps = ['creme_core']
        role.save()

        admin = get_user_model().objects.create(username='chloe', role=role)
        admin.role = role

        field.user = admin
        self.assertEqual([('create', _(u'Add'), True,
                           {'title': _(u'Add'),
#                            'url':   '/creme_config/persons/position/add_widget/',
                            'url':   self.ADD_URL,
                           },
                          )
                         ],
                         field.widget.actions
                        )

        field.user = None
        self.assertFalse(hasattr(field.widget, 'actions'))

    def test_queryset01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in Position.objects.all())

        with self.assertNoException():
            choices = list(field.choices)

        self.assertEqual(positions, choices)

    def test_queryset02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        field.user = self._create_superuser()

        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in Position.objects.all())

        with self.assertNoException():
            options = field.widget.delegate._get_options()

        self.assertEqual(positions, options)

    def test_filtered_queryset01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=Position.objects.filter(pk=1))

        with self.assertNoException():
            choices = list(field.choices)

        self.assertEqual([(u'', u'---------'),
                          (1, Position.objects.get(pk=1).title),
                         ],
                         choices
                        )

    def test_filtered_queryset02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=Position.objects.filter(pk=1))
        field.user = self._create_superuser()

        with self.assertNoException():
            options = field.widget.delegate._get_options()

        self.assertEqual([(u'', u'---------'),
                          (1, Position.objects.get(pk=1).title),
                         ],
                         options
                        )

    def test_queryset_property01(self):
        "No action"
        field = CreatorModelChoiceField(queryset=Position.objects.none())

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual([(u'', u'---------')], list(field.widget.choices))

        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in Position.objects.all())

        field.queryset = Position.objects.all()

        self.assertFalse(hasattr(field.widget, 'actions'))
        self.assertEqual(positions, list(field.choices))

    def test_queryset_property02(self):
        "With action"
        field = CreatorModelChoiceField(queryset=Position.objects.none())
        field.user = self._create_superuser()

        self.assertEqual([(u'', u'---------')], field.widget.delegate._get_options())

        positions = [(u'', u'---------')]
        positions.extend((p.pk, unicode(p)) for p in Position.objects.all())

        field.queryset = Position.objects.all()
        self.assertEqual(positions, field.widget.delegate._get_options())

    def test_create_action_url(self):
        field = CreatorModelChoiceField(Position.objects.all())

        self.assertIsNone(field.create_action_url)
        self.assertEqual('/creme_config/persons/position/add_widget/',
                         field._build_create_action_url('persons', 'position')
                        )

        url = '/persons/config/position/from_widget/add/'
        field.create_action_url = url
        self.assertEqual(url, field.create_action_url)
        self.assertEqual(url, field._build_create_action_url('persons', 'position'))
