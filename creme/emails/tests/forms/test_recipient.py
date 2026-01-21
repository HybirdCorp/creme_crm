from ..base import _EmailsTestCase


class RecipientFormsTestCase(_EmailsTestCase):
    def test_detect_end_line(self):
        from creme.emails.forms.recipient import _detect_end_line

        class FakeUploadedFile:
            def __init__(self, chunks):
                self._chunks = chunks

            def chunks(self):
                yield from self._chunks

        def detect(chunks):
            return _detect_end_line(FakeUploadedFile(chunks))

        self.assertEqual('\n', detect([]))
        self.assertEqual('\n', detect(['abcde']))

        self.assertEqual('\n',   detect(['abcde\nefgij']))
        self.assertEqual('\r',   detect(['abcde\refgij']))
        self.assertEqual('\r\n', detect(['abcde\r\nefgij']))

        self.assertEqual('\n',   detect(['abcdeefgij', 'ih\nklmonp']))
        self.assertEqual('\r',   detect(['abcdeefgij', 'ih\rklmonp']))
        self.assertEqual('\r\n', detect(['abcdeefgij', 'ih\r\nklmonp']))

        self.assertEqual('\r',   detect(['abcdeefgij\r', 'ih\rklmonp']))
        self.assertEqual('\r\n', detect(['abcdeefgij\r', '\nklmonp']))

        self.assertEqual('\r', detect(['abcdeefgij\r', 'klmo\nnp']))
        self.assertEqual('\r', detect(['abcdeefgij\r', 'klmonp']))
