# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase

    from creme.creme_core.utils.content_type import as_ctype
    from creme.creme_core.models import FakeOrganisation
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class ContentTypeTestCase(CremeTestCase):
    def test_as_ctype(self):
        ctype = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertIs(ctype, as_ctype(ctype))
        self.assertEqual(ctype, as_ctype(FakeOrganisation))
        self.assertEqual(ctype, as_ctype(FakeOrganisation()))
