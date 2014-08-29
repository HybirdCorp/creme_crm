 # -*- coding: utf-8 -*-

from django.utils.simplejson.encoder import JSONEncoder

from creme.creme_core.tests.base import CremeTestCase

#from creme.persons.models import Contact


class _ActivitiesTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'activities', 'persons')
        CremeTestCase.setUpClass()

    #def login(self, is_superuser=True, other_is_owner=False):
    def login(self, is_superuser=True, other_is_owner=False,
              allowed_apps=('activities', 'persons'), **kwargs):
        super(_ActivitiesTestCase, self).login(is_superuser,
                                               #allowed_apps=['activities', 'persons'],
                                               allowed_apps=allowed_apps,
                                               **kwargs
                                              ) #'creme_core'

        ##todo: in creme_core ??
        ##user = self.user
        ##other = self.other_user
        ##create_contact = Contact.objects.create
        ##owner = other if other_is_owner else user
        ###self.contact = create_contact(user=owner, first_name='Kirika',
                                      ####last_name=u'Yūmura', is_user=user, #XXX: seems cause problem on MySQL TODO: inspect further
                                      ###last_name=u'Yûmura', is_user=user,
                                     ###)
        ###self.other_contact = create_contact(user=owner, first_name='Mireille',
                                            ###last_name='Bouquet', is_user=other,
                                           ###)
        ##self.contact = self.get_object_or_fail(Contact, is_user=user)
        ##self.other_contact = self.get_object_or_fail(Contact, is_user=other)
        #self.contact = self.user.linked_contact #todo: still useful ??
        #self.other_contact = self.other_user.linked_contact

    def _acttype_field_value(self, atype_id, subtype_id=None):
        return JSONEncoder().encode({'type': atype_id, 'sub_type': subtype_id})
