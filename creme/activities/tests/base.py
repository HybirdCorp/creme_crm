 # -*- coding: utf-8 -*-

from json import dumps as json_dump

from creme.creme_core.tests.base import CremeTestCase


class _ActivitiesTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'activities', 'persons')
        CremeTestCase.setUpClass()

    #def login(self, is_superuser=True, other_is_owner=False):
    def login(self, is_superuser=True, other_is_owner=False,
              allowed_apps=('activities', 'persons'), **kwargs):
        return super(_ActivitiesTestCase, self).login(is_superuser,
                                               #allowed_apps=['activities', 'persons'],
                                               allowed_apps=allowed_apps,
                                               **kwargs
                                              ) #'creme_core'

    def _acttype_field_value(self, atype_id, subtype_id=None):
        return json_dump({'type': atype_id, 'sub_type': subtype_id})
