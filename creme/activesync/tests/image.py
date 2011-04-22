# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from StringIO import StringIO
from os.path import dirname, join, abspath
import base64

from django.test import TestCase
from django.conf import settings

from activesync.utils import get_b64encoded_img_of_max_weight


class ActiveSyncImageTestCase(TestCase):
    def setUp(self):
        self.image_path = join(dirname(abspath(__file__)), 'data', 'creme.png')

    def test_PIL(self):
        try:
            from PIL import Image
        except ImportError:
            self.fail(u"You have to install PIL to use correctly activesync features")

    def test_get_b64encoded_img_of_max_weight01(self):
        b64_content = get_b64encoded_img_of_max_weight(self.image_path, settings.PICTURE_LIMIT_SIZE)

        self.assertTrue(len(b64_content) < settings.PICTURE_LIMIT_SIZE)

        image = open(self.image_path, 'r')
        image_str = StringIO()
        with open(self.image_path) as f:
            for ch in f.read(1024):
                image_str.write(ch)

        self.assertNotEqual(base64.b64decode(b64_content), image_str.getvalue())

        image_str.close()