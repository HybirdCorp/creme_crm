 # -*- coding: utf-8 -*-

skip_activities_tests = False

try:
    from json import dumps as json_dump
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from .. import activity_model_is_custom

    skip_activities_tests = activity_model_is_custom()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomActivity(test_func):
    return skipIf(skip_activities_tests, 'Custom Activity model in use')(test_func)


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
