# -*- coding: utf-8 -*-

from django.http import Http404

from creme.creme_core.models import (
    FakeFolderCategory,
    FakePosition,
    FakeSector,
)
from creme.creme_core.shortcuts import get_bulk_or_404

from .base import CremeTestCase


class ShortcutsTestCase(CremeTestCase):
    def test_get_bulk_or_404_01(self):
        "Argument is a model."
        s1, s2 = FakeSector.objects.all()[:2]

        bulk = get_bulk_or_404(FakeSector, [s1.id, s2.id])
        self.assertDictEqual({s1.id: s1, s2.id: s2}, bulk)

        with self.assertRaises(Http404) as cm:
            get_bulk_or_404(FakeSector, [s1.id, self.UNUSED_PK])

        self.assertEqual(
            f'These IDs cannot be found: {self.UNUSED_PK}',
            cm.exception.args[0],
        )

        # Invalid argument for IDs
        with self.assertRaises(ValueError):
            get_bulk_or_404([s1, s2], [s1.id])

    def test_get_bulk_or_404_02(self):
        "Argument is a queryset."
        s1, s2 = FakeSector.objects.all()[1:3]

        bulk = get_bulk_or_404(FakeSector.objects.all(), [s1.id, s2.id])
        self.assertDictEqual({s1.id: s1, s2.id: s2}, bulk)

    def test_get_bulk_or_404_03(self):
        "Argument is a manager."
        p1, p2 = FakePosition.objects.all()[:2]

        bulk = get_bulk_or_404(FakePosition.objects, [p1.id, p2.id])
        self.assertDictEqual({p1.id: p1, p2.id: p2}, bulk)

    def test_get_bulk_or_404_04(self):
        "Argument <field_name>."
        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Pix')
        cat2 = create_cat(name='Music')
        create_cat(name='Video')

        bulk = get_bulk_or_404(
            FakeFolderCategory.objects, [cat1.name, cat2.name], field_name='name',
        )
        self.assertDictEqual({cat1.name: cat1, cat2.name: cat2}, bulk)

    def test_get_bulk_or_404_05(self):
        "id_list=None."
        create_cat = FakeFolderCategory.objects.create
        cat1 = create_cat(name='Pix')
        cat2 = create_cat(name='Music')
        cat3 = create_cat(name='Video')

        bulk = get_bulk_or_404(FakeFolderCategory.objects)
        self.assertDictEqual({cat1.id: cat1, cat2.id: cat2, cat3.id: cat3}, bulk)

    def test_get_bulk_or_404_06(self):
        "Inr ID as strings."
        s1, s2 = FakeSector.objects.all()[:2]

        bulk = get_bulk_or_404(FakeSector, [str(s1.id), str(s2.id)])
        self.assertDictEqual({s1.id: s1, s2.id: s2}, bulk)

        with self.assertRaises(Http404) as cm:
            get_bulk_or_404(FakeSector, [str(s1.id), f'{self.UNUSED_PK}'])

        self.assertEqual(
            f'These IDs cannot be found: {self.UNUSED_PK}',
            cm.exception.args[0],
        )

    def test_get_bulk_or_404_07(self):
        "Duplicated."
        s1, s2 = FakeSector.objects.all()[:2]

        bulk = get_bulk_or_404(FakeSector, [s1.id, s2.id, str(s1.id)])
        self.assertDictEqual({s1.id: s1, s2.id: s2}, bulk)

        with self.assertRaises(Http404) as cm:
            get_bulk_or_404(FakeSector, [s1.id, str(s1.id), 2048])

        self.assertEqual(
            'These IDs cannot be found: 2048',
            cm.exception.args[0],
        )
