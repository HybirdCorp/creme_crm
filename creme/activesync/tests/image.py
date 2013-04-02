# -*- coding: utf-8 -*-

try:
    import base64
    from os.path import dirname, join, abspath
    from StringIO import StringIO

    from django.conf import settings

    from creme.creme_core.tests.base import CremeTestCase

    from creme.activesync.utils import get_b64encoded_img_of_max_weight
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class ActiveSyncImageTestCase(CremeTestCase):
    def setUp(self):
        self.image_path = join(dirname(abspath(__file__)), 'data', 'creme.png')

    def test_PIL(self):
        try:
            from PIL import Image
        except ImportError:
            self.fail(u"You have to install PIL to use correctly activesync features")

    def test_get_b64encoded_img_of_max_weight01(self):
        b64_content = get_b64encoded_img_of_max_weight(self.image_path, settings.PICTURE_LIMIT_SIZE)

        self.assertLess(len(b64_content), settings.PICTURE_LIMIT_SIZE)

        #image = open(self.image_path, 'r')
        image_str = StringIO()
        with open(self.image_path) as f:
            for ch in f.read(1024):
                image_str.write(ch)

        self.assertNotEqual(base64.b64decode(b64_content), image_str.getvalue())

        image_str.close()
