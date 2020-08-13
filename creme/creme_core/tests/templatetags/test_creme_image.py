from os import path

from django.conf import settings
from django.template import Context, Template

from ..base import CremeTestCase


class CremeImageTagsTestCase(CremeTestCase):
    def test_image_size(self):
        dir_path = path.join(settings.CREME_ROOT, 'static', 'common', 'images')
        img_path1 = path.join(dir_path, '500_200.png')  # 200x200px
        img_path2 = path.join(dir_path, 'creme_logo.png')  # 569x170px
        self.assertTrue(path.exists(img_path1))
        self.assertTrue(path.exists(img_path2))

        with self.assertNoException():
            template = Template(
                r'{% load creme_image %}'
                r'{% image_size path=path1 as sizeA %}'
                r'{% image_size path=path2 as sizeB %}'
                r'{{sizeA.0}}x{{sizeA.1}}#'
                r'{{sizeB.0}}x{{sizeB.1}}'
            )
            render = template.render(Context({
                'path1': img_path1,
                'path2': img_path2,
            }))

        self.assertEqual('200x200#569x170', render.strip())

    def test_image_scale_to_frame01(self):
        "Only width."
        with self.assertNoException():
            template = Template(
                r'{% load creme_image %}'
                r'{% image_scale_to_frame size=size width=320 as sizeA %}'
                r'{% image_scale_to_frame size=size width=100 as sizeB %}'
                r'{% image_scale_to_frame size=size width=640 as sizeC %}'
                r'{{sizeA.0}}x{{sizeA.1}}#'
                r'{{sizeB.0}}x{{sizeB.1}}#'
                r'{{sizeC.0}}x{{sizeC.1}}'
            )
            render = template.render(Context({'size': (320, 240)}))

        self.assertEqual('320x240#100x75#640x480', render.strip())

    def test_image_scale_to_frame02(self):
        "Only height."
        with self.assertNoException():
            template = Template(
                r'{% load creme_image %}'
                r'{% image_scale_to_frame size=size height=240 as sizeA %}'
                r'{% image_scale_to_frame size=size height=100 as sizeB %}'
                r'{% image_scale_to_frame size=size height=480 as sizeC %}'
                r'{{sizeA.0}}x{{sizeA.1}}#'
                r'{{sizeB.0}}x{{sizeB.1}}#'
                r'{{sizeC.0}}x{{sizeC.1}}'
            )
            render = template.render(Context({'size': (320, 240)}))

        self.assertEqual('320x240#133x100#640x480', render.strip())

    def test_image_scale_to_frame03(self):
        "Width & height."
        with self.assertNoException():
            template = Template(
                r'{% load creme_image %}'
                r'{% image_scale_to_frame size=size height=240 width=320 as sizeA %}'
                r'{% image_scale_to_frame size=size width=160 height=160 as sizeB %}'
                r'{% image_scale_to_frame size=size width=160 height=100 as sizeC %}'
                r'{% image_scale_to_frame size=size width=960 height=480 as sizeD %}'
                r'{{sizeA.0}}x{{sizeA.1}}#'
                r'{{sizeB.0}}x{{sizeB.1}}#'
                r'{{sizeC.0}}x{{sizeC.1}}#'
                r'{{sizeD.0}}x{{sizeD.1}}'
            )
            render = template.render(Context({'size': (320, 240)}))

        self.assertEqual('320x240#160x120#133x100#640x480', render.strip())

    def test_image_scale_to_frame04(self):
        "Zero size."
        with self.assertNoException():
            template = Template(
                r'{% load creme_image %}'
                r'{% image_scale_to_frame size=size1 height=240 width=320 as sizeA %}'
                r'{% image_scale_to_frame size=size2 width=160 height=160 as sizeB %}'
                r'{{sizeA.0}}x{{sizeA.1}}#'
                r'{{sizeB.0}}x{{sizeB.1}}'
            )
            render = template.render(Context({
                'size1': (320, 0),
                'size2': (0, 240),
            }))

        self.assertEqual('0x0#0x0', render.strip())
