# -*- coding: utf-8 -*-

skip_activities_tests = False

try:
    from json import dumps as json_dump
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons import get_contact_model, get_organisation_model

    from .. import activity_model_is_custom, get_activity_model

    skip_activities_tests = activity_model_is_custom()
    Activity = get_activity_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Contact = get_contact_model()
Organisation = get_organisation_model()


def skipIfCustomActivity(test_func):
    return skipIf(skip_activities_tests, 'Custom Activity model in use')(test_func)


class _ActivitiesTestCase(CremeTestCase):
    def login(self, is_superuser=True, is_staff=False,
              allowed_apps=('activities', 'persons'), *args, **kwargs):
        return super(_ActivitiesTestCase, self).login(is_superuser=is_superuser,
                                                      is_staff=is_staff,
                                                      allowed_apps=allowed_apps,
                                                      *args, **kwargs
                                                     )

    def _acttype_field_value(self, atype_id, subtype_id=None):
        return json_dump({'type': atype_id, 'sub_type': subtype_id})
