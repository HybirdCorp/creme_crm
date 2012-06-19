# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from django.contrib.auth.models import User

    #from creme_core import autodiscover
    from creme_core.tests.forms.base import CremeTestCase
    from creme_core.models import UserRole
    from creme_config.forms.fields import CreatorModelChoiceField

    from persons.models.other_models import Position  #need CremeEntity
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CreatorModelChoiceFieldTestCase', )


class CreatorModelChoiceFieldTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'persons')
        cls.autodiscover()

    def test_actions_not_admin(self):
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        self.assertEqual([], field.widget.actions)

        field.user = User.objects.create_user(username='averagejoe', email='averagejoe@company.com')
        self.assertEqual([('create', _(u'Add'), False, {'title':_(u"Can't add"),
                                                        'url':'/creme_config/persons/position/add_widget/'})], field.widget.actions)

        field.user = None
        self.assertEqual([], field.widget.actions)

    def test_actions_admin(self):
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        self.assertEqual([], field.widget.actions)

        role = UserRole(name='CEO')
        role.admin_4_apps = ['persons']
        role.save()

        #field.user = User.objects.create_superuser(username='superjoe', email='superjoe@company.com', password='')
        admin = User.objects.create(username='chloe', role=role)
        admin.role = role

        field.user = admin
        self.assertEqual([('create', _(u'Add'), True, {'title':_(u'Add'),
                                                       'url':'/creme_config/persons/position/add_widget/'})], field.widget.actions)

        field.user = None
        self.assertEqual([], field.widget.actions)

    def test_queryset(self):
        field = CreatorModelChoiceField(queryset=Position.objects.all())
        positions = [(u'', u'---------')]
        positions.extend([(p.pk, unicode(p)) for p in Position.objects.all()])

        self.assertEqual([], field.widget.actions)
        self.assertEquals(positions, field.widget.delegate._get_options())

    def test_filtered_queryset(self):
        field = CreatorModelChoiceField(queryset=Position.objects.filter(pk=1))
        self.assertEqual([], field.widget.actions)
        self.assertEquals([(u'', u'---------'), (1, Position.objects.filter(pk=1).get().title)], field.widget.delegate._get_options())

    def test_queryset_property(self):
        field = CreatorModelChoiceField(queryset=Position.objects.none())

        self.assertEqual([], field.widget.actions)
        self.assertEquals([(u'', u'---------')], field.widget.delegate._get_options())

        positions = [(u'', u'---------')]
        positions.extend([(p.pk, unicode(p)) for p in Position.objects.all()])

        field.queryset = Position.objects.all()

        self.assertEqual([], field.widget.actions)
        self.assertEquals(positions, field.widget.delegate._get_options())

    def test_create_action_url(self):
        field = CreatorModelChoiceField(Position)
        self.assertIsNone(field.create_action_url)
        self.assertEqual('/creme_config/persons/position/add_widget/', field._build_create_action_url('persons', 'position'))

        field.create_action_url = '/persons/config/position/from_widget/add/'
        self.assertEqual('/persons/config/position/from_widget/add/', field.create_action_url)
        self.assertEqual('/persons/config/position/from_widget/add/', field._build_create_action_url('persons', 'position'))
