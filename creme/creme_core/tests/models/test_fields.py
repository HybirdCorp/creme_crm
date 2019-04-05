# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase

    from creme.creme_core.models import EntityFilter, FieldsConfig, FakeContact
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class ModelFieldsTestCase(CremeTestCase):
    def test_CTypeForeignKey01(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        efilter = EntityFilter.objects.create(
            pk='creme_core-test_fakecontact',
            entity_type=ct,
        )
        self.assertEqual(ct, self.refresh(efilter).entity_type)

    def test_CTypeForeignKey02(self):
        "Set a model class directly."
        with self.assertNoException():
            efilter = EntityFilter.objects.create(
                pk='creme_core-test_fakecontact',
                entity_type=FakeContact,
            )

        self.assertEqual(ContentType.objects.get_for_model(FakeContact),
                         self.refresh(efilter).entity_type
                        )

    def test_CTypeOneToOneField01(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        fconf = FieldsConfig.objects.create(content_type=ct)
        self.assertEqual(ct, self.refresh(fconf).content_type)

    def test_CTypeOneToOneField02(self):
        "Set a model class directly."
        with self.assertNoException():
            fconf = FieldsConfig.objects.create(content_type=FakeContact)

        self.assertEqual(ContentType.objects.get_for_model(FakeContact),
                         self.refresh(fconf).content_type
                        )