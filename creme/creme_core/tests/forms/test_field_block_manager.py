# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from ..fake_forms import FakeContactForm
    from ..base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class FieldBlockManagerTestCase(CremeTestCase):
    def test_iter(self):
        user = self.login()

        block_vname = u'Particulars'

        class TestFakeContactForm(FakeContactForm):
            blocks = FakeContactForm.blocks.new(('particulars', block_vname,
                                                 ['phone', 'mobile', 'email', 'url_site']
                                                )
                                               )

        blocks_group = TestFakeContactForm(user=user).get_blocks()
        blocks = list(blocks_group)

        self.assertEqual(2, len(blocks))

        # ------------------
        block1 = blocks[0]
        self.assertIsInstance(block1, tuple)
        self.assertEqual(2, len(block1))
        self.assertEqual(_(u'General information'), unicode(block1[0]))

        fields = block1[1]
        self.assertIsInstance(fields, list)

        with self.assertNoException():
            bfield, required = fields[0]

        self.assertIs(required, True)
        self.assertFalse(bfield.is_hidden)
        self.assertEqual('id_user', bfield.auto_id)

        # ------------------
        block2 = blocks[1]
        self.assertEqual(block_vname, block2[0])

        fields = block2[1]
        self.assertEqual(4, len(fields))
        self.assertEqual('id_phone', fields[0][0].auto_id)

    def test_getitem(self):
        user = self.login()

        block_id = 'particulars'
        block_vname = u'Particulars'

        class TestFakeContactForm(FakeContactForm):
            blocks = FakeContactForm.blocks.new((block_id, block_vname,
                                                 ['phone', 'mobile', 'email', 'url_site']
                                                )
                                               )

        blocks_group = TestFakeContactForm(user=user).get_blocks()

        with self.assertNoException():
            general_block = blocks_group['general']

        self.assertEqual(_(u'General information'), unicode(general_block[0]))

        with self.assertNoException():
            p_block = blocks_group[block_id]

        self.assertEqual(block_vname, p_block[0])

        fields = p_block[1]
        self.assertEqual(4, len(fields))
        self.assertEqual('id_mobile', fields[1][0].auto_id)

    def test_invalid_field(self):
        user = self.login()

        block_id = 'particulars'
        block_vname = u'Particulars'

        class TestFakeContactForm(FakeContactForm):
            class Meta(FakeContactForm.Meta):
                exclude = ('mobile', )  # <===

            blocks = FakeContactForm.blocks.new((block_id, block_vname,
                                                 # 'mobile' is excluded
                                                 ['phone', 'mobile', 'email', 'url_site']
                                                )
                                               )

        form = TestFakeContactForm(user=user)

        with self.assertNoException():
            block = form.get_blocks()[block_id]

        self.assertEqual(block_vname, block[0])

        fields = block[1]
        self.assertEqual(3, len(fields))
        self.assertEqual('id_email', fields[1][0].auto_id)
