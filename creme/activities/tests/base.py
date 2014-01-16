 # -*- coding: utf-8 -*-

from creme.creme_core.tests.base import CremeTestCase

from creme.persons.models import Contact


class _ActivitiesTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities') #'persons'

    def login(self, is_superuser=True, other_is_owner=False):
        super(_ActivitiesTestCase, self).login(is_superuser,
                                               allowed_apps=['activities', 'persons'],
                                              ) #'creme_core'

        #TODO: in creme_core ??
        user = self.user
        other = self.other_user
        create_contact = Contact.objects.create
        owner = other if other_is_owner else user
        self.contact = create_contact(user=owner, first_name='Kirika',
                                      #last_name=u'Yūmura', is_user=user, #XXX: seems cause problem on MySQL TODO: inspect further
                                      last_name=u'Yûmura', is_user=user,
                                     )
        self.other_contact = create_contact(user=owner, first_name='Mireille',
                                            last_name='Bouquet', is_user=other,
                                           )
