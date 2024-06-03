from parameterized import parameterized

from ..base import CremeTestCase


class StaticViewTestCase(CremeTestCase):
    @parameterized.expand([
        (None, 'SAMEORIGIN'),
        ('DENY', 'SAMEORIGIN'),
        ('SAMEORIGIN', 'SAMEORIGIN'),
    ])
    def test_tiny_mce_assets(self, x_frame_options, expected):
        with self.settings(X_FRAME_OPTIONS=x_frame_options):
            response = self.client.get('/tiny_mce/tiny_mce_popup.js')
            self.assertEqual(response.headers['X-Frame-Options'], expected)
