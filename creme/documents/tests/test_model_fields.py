from django.db.models import Q

from ..constants import MIMETYPE_PREFIX_IMG
from ..models.fields import (
    _build_limit_choices_to,
    _deconstruct_limit_choices_to,
)
from .base import _DocumentsTestCase


class ImageFieldsTestCase(_DocumentsTestCase):
    def test_build_limit_choices_to01(self):
        "Q case."
        q1 = Q(mime_type__name__startswith=MIMETYPE_PREFIX_IMG)
        self.assertEqual(_build_limit_choices_to(None), q1)

        q2 = Q(title__startswith='Birthday')
        self.assertEqual(_build_limit_choices_to(q2), q1 & q2)

    def test_build_limit_choices_to02(self):
        "Dict case."
        d2 = {'title__startswith': 'Birthday'}
        self.assertEqual(
            _build_limit_choices_to(d2),
            {**d2, 'mime_type__name__startswith': MIMETYPE_PREFIX_IMG},
        )

    def test_deconstruct_limit_choices_to01(self):
        "Q case."
        q1 = Q(mime_type__name__startswith=MIMETYPE_PREFIX_IMG)
        self.assertIsNone(_deconstruct_limit_choices_to(q1))

        q2 = Q(title__startswith='Birthday')
        limit = q1 & q2
        deconstructed = _deconstruct_limit_choices_to(limit)
        self.assertEqual(q2, deconstructed)
        self.assertIsNot(deconstructed, limit)

        self.assertEqual(q2, _deconstruct_limit_choices_to(q1 & q1 & q2))

    def test_deconstruct_limit_choices_to02(self):
        "Dict case."
        d1 = {'mime_type__name__startswith': MIMETYPE_PREFIX_IMG}
        self.assertIsNone(_deconstruct_limit_choices_to(d1))
        self.assertTrue(d1)

        d2 = {'title__startswith': 'Birthday'}
        limit = {**d1, **d2}
        deconstructed = _deconstruct_limit_choices_to(limit)
        self.assertEqual(d2, deconstructed)
        self.assertIsNot(deconstructed, limit)
