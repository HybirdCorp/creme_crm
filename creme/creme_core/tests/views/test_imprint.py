# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.urls import reverse
from django.utils.timezone import now

from creme.creme_core.bricks import ImprintsBrick
from creme.creme_core.core.imprint import imprint_manager
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    FakeOrganisation,
    Imprint,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin, ViewsTestCase


class ImprintViewsTestCase(ViewsTestCase, BrickTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        BrickDetailviewLocation.objects.create_if_needed(
            brick=ImprintsBrick, order=1, zone=BrickDetailviewLocation.LEFT,
        )
        BrickHomeLocation.objects.create(brick_id=ImprintsBrick.id_, order=1)

    def test_detailview(self):
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Middle Earth')
        self.assertFalse(Imprint.objects.all())

        self.assertGET200(orga.get_absolute_url())

        imprints = Imprint.objects.all()
        self.assertEqual(1, len(imprints))

        imprint = imprints[0]
        self.assertDatetimesAlmostEqual(now(), imprint.date)
        self.assertEqual(imprint.entity.get_real_entity(), orga)
        self.assertEqual(imprint.user, user)

    def test_granularity01(self):
        "Delay is not passed."
        self.assertEqual(timedelta(hours=2), imprint_manager.get_granularity(FakeOrganisation))

        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Middle Earth')

        self.assertGET200(orga.get_absolute_url())
        self.assertGET200(orga.get_absolute_url())

        imprints = Imprint.objects.all()
        self.assertEqual(1, len(imprints))  # not 2

        imprint = imprints[0]
        self.assertDatetimesAlmostEqual(now(), imprint.date)
        self.assertEqual(imprint.entity.get_real_entity(), orga)
        self.assertEqual(imprint.user, user)

        # --
        Imprint.objects.filter(id=imprint.id).update(date=now() - timedelta(minutes=119))
        self.assertGET200(orga.get_absolute_url())
        self.assertEqual(1, Imprint.objects.count())  # still not 2

    def test_brick01(self):
        "Detailview"
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='Middle Earth')
        self.assertGET200(orga.get_absolute_url())

        response = self.assertGET200(orga.get_absolute_url())

        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, ImprintsBrick.id_)
        self.assertBrickHasClass(brick_node, 'creme_core-imprints-brick')
        self.assertBrickHasNotClass(brick_node, 'is-empty')

        link_node = brick_node.find(
            f".//a[@href='{user.linked_contact.get_absolute_url()}']"
        )
        self.assertIsNotNone(link_node)
        self.assertEqual(str(user), link_node.text)

    def test_brick02(self):
        "Home."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Middle Earth')
        orga2 = create_orga(name='Mordor')
        self.assertGET200(orga1.get_absolute_url())
        self.assertGET200(orga2.get_absolute_url())

        response = self.assertGET200(reverse('creme_core__home'))
        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, ImprintsBrick.id_)
        self.assertInstanceLink(brick_node, orga1)
        self.assertInstanceLink(brick_node, orga2)

    def test_brick03(self):
        "Not visible for regular users."
        user = self.login(is_superuser=False)

        orga = FakeOrganisation.objects.create(user=user, name='Middle Earth')
        self.assertGET200(orga.get_absolute_url())

        response = self.assertGET200(reverse('creme_core__home'))
        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, ImprintsBrick.id_)
        self.assertBrickHasClass(brick_node, 'is-empty')
        self.assertNoInstanceLink(brick_node, orga)
