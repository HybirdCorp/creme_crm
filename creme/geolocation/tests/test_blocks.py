# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext

    from creme.creme_core.models.entity_filter import EntityFilter, EntityFilterCondition
    from creme.persons.constants import FILTER_MANAGED_ORGA
    from creme.persons.models import Organisation, Contact
    from creme.persons.tests.base import skipIfCustomContact, skipIfCustomOrganisation

    from ..blocks import _MapBlock
    from .base import GeoLocationBaseTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

__all__ = ('_MapBlockTestCase',)


@skipIfCustomContact
@skipIfCustomOrganisation
class _MapBlockTestCase(GeoLocationBaseTestCase):
    def setUp(self):
        super(_MapBlockTestCase, self).setUp()
        self.login()
        self.block = _MapBlock()

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

    def test_filter_choices(self):
        managed_orgas = EntityFilter.objects.get(pk=FILTER_MANAGED_ORGA)

        organisations_title = ugettext(Organisation._meta.verbose_name_plural)
        contacts_title = ugettext(Contact._meta.verbose_name_plural)

        self.assertEqual([], self.block.get_filter_choices(self.user))
        self.assertEqual([], self.block.get_filter_choices(self.user, Contact))
        self.assertEqual([(organisations_title,
                           [(managed_orgas.pk, '%s - %s' % (organisations_title, managed_orgas.name))]
                          )
                         ], self.block.get_filter_choices(self.user, Contact, Organisation))

        self.create_filter('filter-1', 'Contact filter', self.user, Contact, 'first_name', EntityFilterCondition.EQUALS, 'John')
        self.create_filter('filter-2', 'Orga filter', self.user, Organisation, 'name', EntityFilterCondition.EQUALS, 'Le spectre')

        self.assertEqual([], self.block.get_filter_choices(self.user))
        self.assertEqual([(contacts_title,
                           [('filter-1', '%s - %s' % (contacts_title, 'Contact filter'))]
                          )
                         ],
                         self.block.get_filter_choices(self.user, Contact))
        self.assertEqual([(ugettext('Contacts'),
                           [('filter-1', '%s - %s' % (contacts_title, 'Contact filter'))]
                          ),
                          (organisations_title,
                           [(managed_orgas.pk, '%s - %s' % (organisations_title, managed_orgas.name)),
                            ('filter-2', '%s - %s' % (organisations_title, 'Orga filter')),
                           ]
                          )
                         ],
                         self.block.get_filter_choices(self.user, Contact, Organisation))

    def test_filter_choices_private(self):
        managed_orgas = EntityFilter.objects.get(pk=FILTER_MANAGED_ORGA)

        organisations_title = ugettext(Organisation._meta.verbose_name_plural)
        contacts_title = ugettext(Contact._meta.verbose_name_plural)

        self.assertEqual([], self.block.get_filter_choices(self.user))
        self.assertEqual([], self.block.get_filter_choices(self.user, Contact))
        self.assertEqual([(organisations_title,
                           [(managed_orgas.pk, '%s - %s' % (organisations_title, managed_orgas.name))]
                          )
                         ], self.block.get_filter_choices(self.user, Contact, Organisation))

        self.create_filter('filter-1', 'Contact filter', self.user, Contact, 'first_name', EntityFilterCondition.EQUALS, 'John')
        self.create_filter('filter-2', 'Orga filter', self.other_user, Organisation, 'name', EntityFilterCondition.EQUALS, 'Le spectre')

        self.assertEqual([], self.block.get_filter_choices(self.user))
        self.assertEqual([(contacts_title,
                           [('filter-1', '%s - %s' % (contacts_title, 'Contact filter'))]
                          )
                         ],
                         self.block.get_filter_choices(self.user, Contact))
        self.assertEqual([(ugettext('Contacts'),
                           [('filter-1', '%s - %s' % (contacts_title, 'Contact filter'))]
                          ),
                          (organisations_title,
                           [(managed_orgas.pk, '%s - %s' % (organisations_title, managed_orgas.name))]
                          )
                         ],
                         self.block.get_filter_choices(self.user, Contact, Organisation))

