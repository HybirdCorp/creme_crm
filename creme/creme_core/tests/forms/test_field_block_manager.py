# -*- coding: utf-8 -*-

from django import forms
from django.forms.boundfield import BoundField

from creme.creme_core.forms.base import BoundFieldBlocks, FieldBlockManager

from ..base import CremeTestCase
from ..fake_forms import FakeContactForm


class FieldBlockManagerTestCase(CremeTestCase):
    def test_init_error(self):
        with self.assertRaises(TypeError):
            FieldBlockManager('names-Names-*')

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

        # self.assertIsInstance(names_group, tuple)
        # self.assertEqual(2, len(names_group))
        # self.assertEqual('Names', names_group[0])
        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('Names', names_group.label)

        # items = names_group[1]
        # self.assertIsInstance(items, list)
        # self.assertEqual(2, len(items))
        names_bfields = names_group.bound_fields
        self.assertEqual(2, len(names_bfields))

        # # --
        # item1 = items[0]
        # self.assertIsInstance(item1, tuple)
        # self.assertEqual(2, len(item1))
        # self.assertIs(item1[1], False)
        #
        # bound_field1 = item1[0]
        bound_field1 = names_bfields[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('first_name', bound_field1.name)
        self.assertEqual('id_first_name', bound_field1.auto_id)

        # --
        # bfield2, required2 = items[1]
        # self.assertEqual('last_name', bfield2.name)
        self.assertEqual('last_name', names_bfields[1].name)
        # self.assertIs(required2, True)

        # --
        with self.assertNoException():
            details_group = blocks['details']

        # self.assertEqual('Details', details_group[0])
        self.assertEqual('Details', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],  # The order of the block info is used
            # [bfield.name for bfield, required in details_group[1]]
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

        fbm = FieldBlockManager(
            {'id': 'names',   'label': 'Names',   'fields': ('first_name', 'last_name')},
            {'id': 'details', 'label': 'Details', 'fields': ['cell', 'phone', 'fax']},
        )
        form = TestForm()

        blocks = fbm.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('Names', names_group.label)

        bfields = names_group.bound_fields
        self.assertEqual(2, len(bfields))

        bound_field1 = bfields[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('first_name', bound_field1.name)

        self.assertEqual('last_name', bfields[1].name)

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
        # self.assertIsInstance(names_group, tuple)
        # self.assertEqual(2, len(names_group))
        # self.assertEqual('Names', names_group[0])
        self.assertIsInstance(names_group, BoundFieldBlocks.BoundFieldBlock)
        self.assertEqual('Names', names_group.label)

        details_group = blocks_list[1]
        # self.assertEqual('Details', details_group[0])
        self.assertEqual('Details', details_group.label)

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
            # [bfield.name for bfield, required in group[1]]
            [bfield.name for bfield in group.bound_fields]
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

        # self.assertEqual(block_vname, block[0])
        self.assertEqual(block_vname, block.label)

        # fields = block[1]
        # self.assertEqual(3, len(fields))
        # self.assertEqual('id_email', fields[1][0].auto_id)
        bound_fields = block.bound_fields
        self.assertEqual(3, len(bound_fields))
        self.assertEqual('id_email', bound_fields[1].auto_id)

    def test_wildcard01(self):
        "Wildcard in first group."
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
            # [bfield.name for bfield, required in blocks['names'][1]]
            [bfield.name for bfield in blocks['names'].bound_fields]
        )
        self.assertListEqual(
            ['phone', 'cell', 'fax'],  # The order of the form-fields is used
            # [bfield.name for bfield, required in blocks['details'][1]]
            [bfield.name for bfield in blocks['details'].bound_fields]
        )

    def test_wildcard02(self):
        "Wildcard in second group."
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name', required=False)
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm = FieldBlockManager(
            ('names',   'Names',   '*'),
            ('details', 'Details', ('phone', 'fax', 'cell')),
        )

        blocks = fbm.build(TestForm())
        self.assertListEqual(
            ['first_name', 'last_name'],
            # [bfield.name for bfield, required in blocks['names'][1]]
            [bfield.name for bfield in blocks['names'].bound_fields]
        )
        self.assertListEqual(
            ['phone', 'fax', 'cell'],
            # [bfield.name for bfield, required in blocks['details'][1]]
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
            str(cm.exception)
        )

    def test_new01(self):
        class TestForm(forms.Form):
            first_name = forms.CharField(label='First name')
            last_name  = forms.CharField(label='Last name')
            phone = forms.CharField(label='Phone')
            cell  = forms.CharField(label='Cell')
            fax   = forms.CharField(label='Fax')

        fbm1 = FieldBlockManager(
            ('names',   'Names', ('last_name', 'first_name')),
        )
        fbm2 = fbm1.new(
            ('details', 'Details', ('cell', 'phone', 'fax')),
        )
        self.assertIsInstance(fbm2, FieldBlockManager)
        self.assertIsNot(fbm2, fbm1)

        form = TestForm()

        blocks = fbm2.build(form)
        with self.assertNoException():
            names_group = blocks['names']

        # self.assertEqual('Names', names_group[0])
        self.assertEqual('Names', names_group.label)
        self.assertListEqual(
            ['last_name', 'first_name'],
            # [bfield.name for bfield, required in names_group[1]]
            [bfield.name for bfield in names_group.bound_fields]
        )

        with self.assertNoException():
            details_group = blocks['details']

        # self.assertEqual('Details', details_group[0])
        self.assertEqual('Details', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            # [bfield.name for bfield, required in details_group[1]]
            [bfield.name for bfield in details_group.bound_fields]
        )

    def test_new02(self):
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

        # self.assertEqual('Names', names_group[0])
        self.assertEqual('Names', names_group.label)
        self.assertListEqual(
            ['last_name', 'first_name'],
            # [bfield.name for bfield, required in names_group[1]]
            [bfield.name for bfield in names_group.bound_fields]
        )

        with self.assertNoException():
            details_group = blocks['details']

        # self.assertEqual('Details extended', details_group[0])
        self.assertEqual('Details extended', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            # [bfield.name for bfield, required in details_group[1]]
            [bfield.name for bfield in details_group.bound_fields]
        )

    def test_new03(self):
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

    def test_new04(self):
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

    def test_new05(self):
        "Dicts arguments."
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
            {'id': 'details', 'label': 'Details extended', 'fields': ('phone', 'fax')},
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
            [bfield.name for bfield in names_group.bound_fields]
        )

        with self.assertNoException():
            details_group = blocks['details']

        self.assertEqual('Details extended', details_group.label)
        self.assertListEqual(
            ['cell', 'phone', 'fax'],
            [bfield.name for bfield in details_group.bound_fields]
        )

    def test_new_error(self):
        fbm1 = FieldBlockManager(
            ('names', 'Names', ('last_name', 'first_name')),
        )
        with self.assertRaises(TypeError):
            fbm1.new('details-Details-*')
