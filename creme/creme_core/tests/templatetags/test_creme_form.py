from itertools import zip_longest

from django import forms

from creme.creme_core.forms.base import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    BoundFieldBlocks,
    FieldBlockManager,
)
from creme.creme_core.templatetags.creme_form import (
    form_gather_blocks_for_layout,
)

from ..base import CremeTestCase


class CremeFormTagsTestCase(CremeTestCase):
    def assertGatheredEqual(self, expected, gathered):
        self.assertIsList(gathered)
        BFB = BoundFieldBlocks.BoundFieldBlock

        def build_gathered_ids(fblocks):
            gathered_ids = []
            for block in fblocks:
                self.assertIsInstance(block, BFB)
                gathered_ids.append(block.id)

            return gathered_ids

        for e1, e2 in zip_longest(expected, gathered):
            if e1 is None:
                self.fail(f'The result is too long, {e2} not expected.')

            if e2 is None:
                self.fail(f'The result is too short, {e1} not found.')

            self.assertIsTuple(e2, length=2)
            self.assertEqual(e1[0], e2[0])

            blocks = e2[1]
            if isinstance(blocks, list):
                self.assertListEqual(e1[1], build_gathered_ids(blocks))
            elif isinstance(blocks, tuple):
                self.assertEqual(2, len(blocks))
                left_blocks, right_blocks = e1[1]
                self.assertListEqual(left_blocks,  build_gathered_ids(blocks[0]))
                self.assertListEqual(right_blocks, build_gathered_ids(blocks[1]))
            else:
                self.fail(f'Bad type: {blocks}')

    def test_form_gather_blocks_for_layout(self):
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')
            address = forms.CharField(label='Address')

        form = TestForm()

        fbm1 = FieldBlockManager(('general', 'Information', '*'))
        self.assertGatheredEqual(
            [('regular', ['general'])],
            form_gather_blocks_for_layout(fbm1.build(form)),
        )

        fbm2 = FieldBlockManager(
            ('general', 'General', '*'),
            ('details', 'Details', ['phone', 'cell', 'fax']),
        )
        self.assertGatheredEqual(
            [('regular', ['general', 'details'])],
            form_gather_blocks_for_layout(fbm2.build(form)),
        )

        fbm3 = FieldBlockManager(
            {
                'id': 'names',
                'label': 'Names',
                'fields': ('last_name', 'first_name'),
                'layout': LAYOUT_DUAL_FIRST,
            },
            {
                'id': 'phones',
                'label': 'Phones',
                'fields': ('phone', 'cell'),
                'layout': LAYOUT_DUAL_SECOND,
            },
            ('other', 'Other', '*'),
        )
        self.assertGatheredEqual(
            [
                ('dual', (['names'], ['phones'])),
                ('regular', ['other']),
            ],
            form_gather_blocks_for_layout(fbm3.build(form)),
        )

        fbm4 = FieldBlockManager(
            {
                'id': 'names',
                'label': 'Names',
                'fields': ('last_name', 'first_name'),
                'layout': LAYOUT_DUAL_FIRST,
            },
            {
                'id': 'phones',
                'label': 'Phones',
                'fields': ('phone', 'cell'),
                'layout': LAYOUT_DUAL_SECOND,
            },
            {
                'id': 'address',
                'label': 'Address',
                'fields': ('address',),
                'layout': LAYOUT_DUAL_FIRST,
            },
            ('other', 'Other', '*'),
        )
        self.assertGatheredEqual(
            [
                ('dual', (['names', 'address'], ['phones'])),
                ('regular', ['other']),
            ],
            form_gather_blocks_for_layout(fbm4.build(form)),
        )
