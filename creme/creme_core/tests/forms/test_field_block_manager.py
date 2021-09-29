# -*- coding: utf-8 -*-

from django import forms
from django.forms.boundfield import BoundField

from creme.creme_core.forms.base import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
    BoundFieldBlocks,
    FieldBlockManager,
)

from ..base import CremeTestCase
from ..fake_forms import FakeContactForm


class FieldBlockManagerTestCase(CremeTestCase):
    def test_init_error(self):
        with self.assertRaises(TypeError) as cm1:
            FieldBlockManager('names-Names-*')
        self.assertEqual(
            'Arguments <blocks> must be tuples or dicts.',
            str(cm1.exception)
        )

        with self.assertRaises(ValueError) as cm2:
            FieldBlockManager({
                'id': 'names', 'label': 'Names', 'fields': '*',
                'layout': 'invalid',  # <==
            })
        self.assertEqual(
            'The layout "invalid" is invalid.',
            str(cm2.exception)
        )

    def test_basic_get_item01(self):
        "Constructor with tuples."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm = FieldBlockManager(
            ('names',   'Names',   ('first_name', 'last_name')),
            ('details', 'Details', ['cell', 'phone', 'fax']),
        )
        form = TestForm()

        blocks = fbm.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('names', names_group.id)
        self.assertEqual('Names', names_group.label)
        self.assertEqual(LAYOUT_REGULAR, names_group.layout)

        names_bfields = names_group.bound_fields
        self.assertEqual(2, len(names_bfields))

        bound_field1 = names_bfields[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('first_name', bound_field1.name)
        self.assertEqual('id_first_name', bound_field1.auto_id)

        # --
        self.assertEqual('last_name', names_bfields[1].name)

        # --
        with self.assertNoException():
            details_group = blocks['details']

        self.assertEqual('Details', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],  # The order of the block info is used
            [bfield.name for bfield in details_group.bound_fields]
        )

        # ---
        with self.assertRaises(KeyError):
            # Already pop
            blocks['names']  # NOQA

    def test_basic_get_item02(self):
        "Constructor with dicts."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        template_details = 'creme_core/generics/blockform/field-block-IMPROVED.html'
        ctxt_details = {'some': 'info'}
        fbm = FieldBlockManager(
            {
                'id': 'names',
                'label': 'Names',
                'fields': ('first_name', 'last_name')
            }, {
                'id': 'details',
                'label': 'Details',
                'fields': ['cell', 'phone', 'fax'],
                'layout': LAYOUT_DUAL_FIRST,
                'template': template_details,
                'context': ctxt_details,
            },
        )
        form = TestForm()

        blocks = fbm.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('Names', names_group.label)
        self.assertEqual(LAYOUT_REGULAR, names_group.layout)
        self.assertEqual(
            'creme_core/generics/blockform/field-block.html',
            names_group.template_name,
        )
        self.assertIsNone(names_group.template_context)

        bfields = names_group.bound_fields
        self.assertEqual(2, len(bfields))

        bound_field1 = bfields[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('first_name', bound_field1.name)

        self.assertEqual('last_name', bfields[1].name)

        # --
        details_group = blocks['details']
        self.assertEqual('Details', details_group.label)
        self.assertEqual(LAYOUT_DUAL_FIRST, details_group.layout)
        self.assertEqual(template_details, details_group.template_name)
        self.assertDictEqual(ctxt_details, details_group.template_context)

    def test_basic_iter(self):
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm = FieldBlockManager(
            ('names',   'Names',   ('first_name', 'last_name')),
            ('details', 'Details', ('cell', 'phone', 'fax')),
        )
        form = TestForm()

        with self.assertNoException():
            blocks_list = [*fbm.build(form)]

        self.assertEqual(2, len(blocks_list))

        names_group = blocks_list[0]
        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('Names', names_group.label)

        self.assertEqual('Details', blocks_list[1].label)

    def test_invalid_field01(self):
        class TestForm(forms.Form):
            last_name = forms.CharField(label='Last name')

        fbm = FieldBlockManager(
            ('names', 'Names', ('invalid', 'last_name')),
        )
        form = TestForm()

        with self.assertNoException():
            blocks = fbm.build(form)

        with self.assertNoException():
            group = blocks['names']

        self.assertListEqual(
            ['last_name'],
            [bfield.name for bfield in group.bound_fields],
        )

    def test_invalid_field02(self):
        user = self.create_user()

        block_id = 'particulars'
        block_vname = 'Particulars'

        class TestFakeContactForm(FakeContactForm):
            class Meta(FakeContactForm.Meta):
                exclude = ('mobile', )  # <===

            blocks = FakeContactForm.blocks.new(
                (
                    block_id, block_vname,
                    # 'mobile' is excluded
                    ['phone', 'mobile', 'email', 'url_site'],
                )
            )

        form = TestFakeContactForm(user=user)

        with self.assertNoException():
            block = form.get_blocks()[block_id]

        self.assertEqual(block_vname, block.label)

        bound_fields = block.bound_fields
        self.assertEqual(3, len(bound_fields))
        self.assertEqual('id_email', bound_fields[1].auto_id)

    def test_wildcard01(self):
        "Wildcard in second group."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm = FieldBlockManager(
            ('names',   'Names',   ('first_name', 'last_name')),
            ('details', 'Details', '*'),
        )

        blocks = fbm.build(TestForm())
        self.assertListEqual(
            ['first_name', 'last_name'],
            [bfield.name for bfield in blocks['names'].bound_fields],
        )
        self.assertListEqual(
            ['phone', 'cell', 'fax'],  # The order of the form-fields is used
            [bfield.name for bfield in blocks['details'].bound_fields],
        )

    def test_wildcard02(self):
        "Wildcard in first group + layout."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm = FieldBlockManager(
            {'id': 'names', 'label': 'Names', 'fields': '*', 'layout': LAYOUT_DUAL_SECOND},
            ('details', 'Details', ('phone', 'fax', 'cell')),
        )

        blocks = fbm.build(TestForm())
        name_block = blocks['names']
        self.assertEqual(LAYOUT_DUAL_SECOND, name_block.layout)
        self.assertListEqual(
            ['first_name', 'last_name'],
            [bfield.name for bfield in name_block.bound_fields]
        )
        self.assertListEqual(
            ['phone', 'fax', 'cell'],
            [bfield.name for bfield in blocks['details'].bound_fields]
        )

    def test_wildcard03(self):
        "Several wildcards => error."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')

        fbm = FieldBlockManager(
            ('names', 'Names', '*'),
            ('details', 'Details', '*'),
        )

        with self.assertRaises(ValueError) as cm:
            fbm.build(TestForm())

        self.assertEqual(
            f'Only one wildcard is allowed: {TestForm}',
            str(cm.exception),
        )

    def test_new01(self):
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell = forms.CharField(label='Cell')
            fax = forms.CharField(label='Fax')

        names_id = 'names'
        details_id = 'details'
        fbm1 = FieldBlockManager(
            (names_id,   'Names', ('last_name', 'first_name')),
        )
        fbm2 = fbm1.new(
            (details_id, 'Details', ('cell', 'phone', 'fax')),
        )
        self.assertIsInstance(fbm2, FieldBlockManager)
        self.assertIsNot(fbm2, fbm1)

        form = TestForm()

        blocks = fbm2.build(form)
        with self.assertNoException():
            names_group = blocks[names_id]

        self.assertEqual('Names', names_group.label)
        self.assertListEqual(
            ['last_name', 'first_name'],
            [bfield.name for bfield in names_group.bound_fields],
        )

        with self.assertNoException():
            details_group = blocks[details_id]

        self.assertEqual('Details',      details_group.label)
        self.assertEqual(LAYOUT_REGULAR, details_group.layout)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            [bfield.name for bfield in details_group.bound_fields],
        )

        self.assertListEqual(
            [names_id, details_id],
            [fb.id for fb in fbm2.build(form)],
        )

    def test_new_merge(self):
        "Block merge."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm1 = FieldBlockManager(
            ('names',   'Names',   ('last_name', 'first_name')),
            ('details', 'Details', ['cell']),
        )
        fbm2 = fbm1.new(
            ('details', 'Details extended', ('phone', 'fax')),
        )
        self.assertIsInstance(fbm2, FieldBlockManager)
        self.assertIsNot(fbm2, fbm1)

        form = TestForm()

        blocks = fbm2.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        self.assertEqual('Names', names_group.label)
        self.assertListEqual(
            ['last_name', 'first_name'],
            [bfield.name for bfield in names_group.bound_fields],
        )

        with self.assertNoException():
            details_group = blocks['details']

        self.assertEqual('Details extended', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            [bfield.name for bfield in details_group.bound_fields],
        )

    def test_new_wildcard01(self):
        "Extend parent wildcard => error."
        fbm1 = FieldBlockManager(
            ('names', 'Names', '*'),
        )

        with self.assertRaises(ValueError) as cm:
            fbm1.new(
                ('names',   'Names',   ['cell']),
                ('details', 'Details', ('phone', 'fax')),
            )

        self.assertEqual(
            'You cannot extend a wildcard (see the form-block with category "names")',
            str(cm.exception)
        )

    def test_new_wildcard02(self):
        "Extend with wildcard => error."
        fbm1 = FieldBlockManager(
            ('names', 'Names', ('first_name', 'last_name')),
        )

        with self.assertRaises(ValueError) as cm:
            fbm1.new(
                ('names', 'Names', '*'),
                ('details', 'Details', ('phone', 'fax')),
            )

        self.assertEqual(
            'You cannot extend with a wildcard (see the form-block with category "names")',
            str(cm.exception)
        )

    def test_new_dictarg(self):
        "Dicts arguments."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')
            address = forms.CharField(label='Address')

        fbm1 = FieldBlockManager(
            {
                'id': 'names',
                'label': 'Names',
                'fields': ('last_name', 'first_name'),
                'layout': LAYOUT_DUAL_FIRST,
            },
            ('details', 'Details', ['cell']),
        )
        fbm2 = fbm1.new(
            {
                'id': 'details',
                'label': 'Details extended',
                'fields': ('phone', 'fax'),
                'layout': LAYOUT_DUAL_SECOND,
            },
            {'id': 'address', 'label': 'Address', 'fields': ['address']},
            {
                'id': 'other',
                'label': 'Other',
                'fields': '*',
                'layout': LAYOUT_DUAL_FIRST,
            },
        )
        self.assertIsInstance(fbm2, FieldBlockManager)
        self.assertIsNot(fbm2, fbm1)

        form = TestForm()

        blocks = fbm2.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        self.assertEqual('Names', names_group.label)
        self.assertEqual(LAYOUT_DUAL_FIRST, names_group.layout)
        self.assertListEqual(
            ['last_name', 'first_name'],
            [bfield.name for bfield in names_group.bound_fields],
        )

        with self.assertNoException():
            details_group = blocks['details']

        self.assertEqual('Details extended', details_group.label)
        self.assertEqual(LAYOUT_DUAL_SECOND, details_group.layout)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            [bfield.name for bfield in details_group.bound_fields],
        )

        self.assertEqual(LAYOUT_REGULAR,    blocks['address'].layout)
        self.assertEqual(LAYOUT_DUAL_FIRST, blocks['other'].layout)

    def test_new_order01(self):
        "<order> argument."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell = forms.CharField(label='Cell')
            fax = forms.CharField(label='Fax')
            address = forms.CharField(label='Address')
            sector = forms.CharField(label='Sector')
            position = forms.CharField(label='Position')
            birthday = forms.DateField(label='Birthday')

        misc_id = 'misc'
        corporate_id = 'corporate'
        names_id = 'names'
        details_id = 'details'
        address_id = 'address'
        fbm1 = FieldBlockManager(
            {
                'id': misc_id,
                'label': 'Misc',
                'fields': ['birthday'],
            },
            {
                'id': details_id,
                'label': 'Details',
                'fields': ['cell'],
            },
            {
                'id': corporate_id,
                'label': 'Corporate',
                'fields': ['sector', 'position'],
            },
        )
        fbm2 = fbm1.new(
            {
                'id': address_id,
                'label': 'Address',
                'fields': ['address'],
                'order': 2,
            },
            {
                'id': details_id,  # We extend this one
                'label': 'Details extended',
                'fields': ['phone', 'fax'],
            },
            {
                'id': names_id,
                'label': 'Names',
                'fields': ('last_name', 'first_name'),
                'order': 0,
            },
        )
        self.assertListEqual(
            [
                names_id,  # order = 0
                misc_id,
                address_id,  # order = 2
                details_id,
                corporate_id,
            ],
            [fb.id for fb in fbm2.build(TestForm())],
        )

    def test_new_order02(self):
        "Big <order> argument."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell = forms.CharField(label='Cell')
            sector = forms.CharField(label='Sector')
            position = forms.CharField(label='Position')

        corporate_id = 'corporate'
        names_id = 'names'
        details_id = 'details'
        fbm1 = FieldBlockManager(
            {
                'id': names_id,
                'label': 'Names',
                'fields': ('last_name', 'first_name'),
            },
        )
        fbm2 = fbm1.new(
            {
                'id': corporate_id,
                'label': 'Corporate',
                'fields': ['sector', 'position'],
                'order': 888,  # <====
            },
            {
                'id': details_id,
                'label': 'Details extended',
                'fields': ['phone', 'cell'],
                'order': 999,  # <====
            },
        )
        self.assertListEqual(
            [names_id, corporate_id, details_id],
            [fb.id for fb in fbm2.build(TestForm())],
        )

    def test_new_order03(self):
        "No <order> in __init__."
        with self.assertRaises(ValueError) as cm:
            FieldBlockManager(
                {
                    'id': 'names',
                    'label': 'Names',
                    'fields': ('last_name', 'first_name'),
                    'order': 0,  # <===
                },
            )

        self.assertEqual(
            'Do not pass <order> information in FieldBlockManager constructor.',
            str(cm.exception),
        )

    def test_new_error(self):
        fbm1 = FieldBlockManager(
            ('names', 'Names', ('last_name', 'first_name')),
        )
        with self.assertRaises(TypeError):
            fbm1.new('details-Details-*')
