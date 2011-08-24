# -*- coding: utf-8 -*-

from creme_core.blocks import RelationsBlock
from creme_core.models.block import BlockState
from creme_core.tests.base import CremeTestCase


class BlockViewTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_config')

    def test_set_state01(self):
        self.login()

        self.assertEqual(0, BlockState.objects.count())

        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 1})

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, BlockState.objects.count())
        try:
            self.assert_(BlockState.objects.get(user=self.user, block_id=block_id).is_open)
        except Exception, e:
            self.fail(e)


        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 0})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, BlockState.objects.count())
        try:
            self.failIf(BlockState.objects.get(user=self.user, block_id=block_id).is_open)
        except Exception, e:
            self.fail(e)

        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={})#No data
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, BlockState.objects.count())
        try:
            self.failIf(BlockState.objects.get(user=self.user, block_id=block_id).is_open)
        except Exception, e:
            self.fail(e)

    def test_set_state02(self):
        self.login()

        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 1, 'show_empty_fields': 1})

        try:
            block_state = BlockState.objects.get(user=self.user, block_id=block_id)
        except Exception, e:
            self.fail(e)

        self.assert_(block_state.is_open)
        self.assert_(block_state.show_empty_fields)

    def test_set_state03(self):
        self.login()

        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 1, 'show_empty_fields': 1})

        self.client.logout()
        self.client.login(username=self.other_user.username, password="test")

        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 0, 'show_empty_fields': 0})

        blocks_states = BlockState.objects.filter(block_id=block_id)

        block_state_user = blocks_states.get(user=self.user)
        block_state_other_user = blocks_states.get(user=self.other_user)

        self.assert_(block_state_user.is_open)
        self.assert_(block_state_user.show_empty_fields)

        self.assertFalse(block_state_other_user.is_open)
        self.assertFalse(block_state_other_user.show_empty_fields)

