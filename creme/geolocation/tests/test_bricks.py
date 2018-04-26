# -*- coding: utf-8 -*-

try:
    from creme.creme_core.models.entity_filter import EntityFilter, EntityFilterCondition

    from creme.persons.constants import FILTER_MANAGED_ORGA, FILTER_CONTACT_ME
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from ..bricks import _MapBrick
    from .base import GeoLocationBaseTestCase, Organisation, Contact
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomContact
@skipIfCustomOrganisation
class _MapBlockTestCase(GeoLocationBaseTestCase):
    def setUp(self):
        super(_MapBlockTestCase, self).setUp()
        self.login()
        self.block = _MapBrick()

        self.contacts_title      = unicode(Contact._meta.verbose_name_plural)
        self.organisations_title = unicode(Organisation._meta.verbose_name_plural)

    def create_filter(self, pk, name, owner, model, field, operator, *values):
        return EntityFilter.create(pk, name, model=model,
                                   user=owner,
                                   is_private=True, is_custom=True,
                                   conditions=[EntityFilterCondition.build_4_field(
                                                   model=model,
                                                   operator=operator,
                                                   name=field, values=values,
                                               ),
                                              ],
                                  )

    def test_filter_choices01(self):
        user = self.user
        self.assertEqual([], self.block.get_filter_choices(user))

        get_efilter = EntityFilter.objects.get
        contact_me    = get_efilter(pk=FILTER_CONTACT_ME)
        managed_orgas = get_efilter(pk=FILTER_MANAGED_ORGA)

        contact_group = (self.contacts_title,
                         [(contact_me.pk, '%s - %s' % (self.contacts_title, contact_me.name))]
                        )
        self.assertEqual([contact_group],
                         self.block.get_filter_choices(user, Contact)
                        )

        orga_group = (self.organisations_title,
                      [(managed_orgas.pk, '%s - %s' % (self.organisations_title, managed_orgas.name))]
                     )
        self.assertEqual([orga_group],
                         self.block.get_filter_choices(user, Organisation)
                        )
        self.assertEqual([contact_group, orga_group],
                         self.block.get_filter_choices(user, Contact, Organisation)
                        )

    def test_filter_choices02(self):
        user = self.user

        get_efilter = EntityFilter.objects.get
        contact_me    = get_efilter(pk=FILTER_CONTACT_ME)
        managed_orgas = get_efilter(pk=FILTER_MANAGED_ORGA)

        EQUALS = EntityFilterCondition.EQUALS
        efilter1 = self.create_filter('filter-1', 'Contact filter', user, Contact,      'first_name', EQUALS, 'John')
        efilter2 = self.create_filter('filter-2', 'Orga filter',    user, Organisation, 'name',       EQUALS, 'Le spectre')

        self.assertEqual([], self.block.get_filter_choices(user))

        contact_group = self.block.get_filter_choices(user, Contact)[0]
        self.assertEqual(self.contacts_title, contact_group[0])

        contact_opt = contact_group[1]
        self.assertIn((contact_me.pk, '%s - %s' % (self.contacts_title, contact_me.name)), contact_opt)
        self.assertIn((efilter1.pk,   '%s - %s' % (self.contacts_title, efilter1.name)),   contact_opt)

        # -----
        orga_group = self.block.get_filter_choices(user, Organisation)[0]
        self.assertEqual(self.organisations_title, orga_group[0])

        orga_opt = orga_group[1]
        self.assertIn((managed_orgas.pk, '%s - %s' % (self.organisations_title, managed_orgas.name)), orga_opt)
        self.assertIn((efilter2.pk,      '%s - %s' % (self.organisations_title, efilter2.name)),      orga_opt)

        # -----
        self.assertEqual([contact_group, orga_group],
                         self.block.get_filter_choices(user, Contact, Organisation)
                        )

    def test_filter_choices_private(self):
        user = self.user
        other_user = self.other_user

        managed_orgas = EntityFilter.objects.get(pk=FILTER_MANAGED_ORGA)
        efilter = self.create_filter('filter-2', 'Orga filter', other_user, Organisation, 'name',
                                     EntityFilterCondition.EQUALS, 'Le spectre'
                                    )

        title = self.organisations_title
        self.assertEqual([(title,
                           [(managed_orgas.pk, '%s - %s' % (title, managed_orgas.name))]
                          )
                         ],
                         self.block.get_filter_choices(user, Organisation)
                        )

        orga_group = self.block.get_filter_choices(other_user, Organisation)[0]
        self.assertEqual(title, orga_group[0])

        orga_opt = orga_group[1]
        self.assertIn((managed_orgas.pk, '%s - %s' % (title, managed_orgas.name)), orga_opt)
        self.assertIn((efilter.pk,       '%s - %s' % (title, efilter.name)),       orga_opt)
