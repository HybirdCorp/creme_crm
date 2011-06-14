# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################
from creme_core.blocks import RelationsBlock
from creme_core.models.block import BlockState
from creme_core.tests.base import CremeTestCase

class BlockViewTestCase(CremeTestCase):
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

