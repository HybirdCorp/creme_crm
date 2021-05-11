# -*- coding: utf-8 -*-

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.tests.base import CremeTestCase


class CoreTestCase(CremeTestCase):
    def test_field_tag_is_valid01(self):
        self.assertTrue(FieldTag.is_valid(FieldTag.VIEWABLE))
        self.assertTrue(FieldTag.is_valid(FieldTag.CLONABLE))
        self.assertTrue(FieldTag.is_valid(FieldTag.OPTIONAL))
        self.assertTrue(FieldTag.is_valid(FieldTag.ENUMERABLE))

    def test_field_tag_is_valid02(self):
        self.assertTrue(FieldTag.is_valid('viewable'))
        self.assertTrue(FieldTag.is_valid('clonable'))
        self.assertTrue(FieldTag.is_valid('optional'))
        self.assertTrue(FieldTag.is_valid('enumerable'))

        self.assertFalse(FieldTag.is_valid('invalid'))

    def test_field_tag_str(self):
        self.assertEqual('viewable', str(FieldTag.VIEWABLE))
        self.assertEqual('clonable', str(FieldTag.CLONABLE))
