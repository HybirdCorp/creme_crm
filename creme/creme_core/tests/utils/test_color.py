from creme.creme_core.utils.color import Color, random_pastel_color

from ..base import CremeTestCase


class ColorTestCase(CremeTestCase):
    def test_rgb(self):
        col = Color('rgb(255, 136, 96)')
        self.assertEqual(255, col.r)
        self.assertEqual(136, col.g)
        self.assertEqual(96,  col.b)
        self.assertEqual('#ff8860', col.html)

    def test_hsl(self):
        col = Color('hsl(197, 69%, 97%)')
        self.assertEqual(242, col.r)
        self.assertEqual(250, col.g)
        self.assertEqual(253, col.b)

    def test_pastel_color(self):
        col1 = random_pastel_color()
        self.assertIsInstance(col1, Color)
        self.assertNotEqual(col1, random_pastel_color())
