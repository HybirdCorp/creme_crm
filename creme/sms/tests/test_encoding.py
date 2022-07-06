from creme.creme_core.tests.base import CremeTestCase
from creme.sms.encoding import gsm_encoded_content


class EncodingTestCase(CremeTestCase):
    def test_gsm_encoded_content(self):
        self.assertEqual(b'Foo', gsm_encoded_content('Foo'))
        self.assertEqual(
            b'The price is 3\x1be',
            gsm_encoded_content('The price is 3€')
        )
        self.assertEqual(
            b'Hi,\x7fhow are you?',
            gsm_encoded_content('Hi,\nhow are you?')
        )
        self.assertEqual(
            b'Hi,\x7fhow are you?',
            gsm_encoded_content('Hi,\nhow are you?')
        )
        self.assertEqual(
            b'Hi \x1b<ROBOTO\x1b>, how are you?',
            gsm_encoded_content('Hi [ROBOTO], how are you?')
        )

        # TODO: complete
