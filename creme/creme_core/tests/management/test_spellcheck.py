import array
from unittest import TestCase

from creme.creme_core.management.commands.i18n_spellcheck import (
    CremePoTokenizer,
)


class CremePoTokenizerTestCase(TestCase):
    def assertTokenizedTextEqual(self, text, expected):
        tokenizer = CremePoTokenizer(text)
        self.assertFalse(tokenizer.looks_like_html(text), f"Text was: {text}")
        tokenizer.preprocess_text()
        self.assertEqual(expected, tokenizer._text, f"Text was: {text}")

    def assertTokenizedHtmlEqual(self, html, expected):
        tokenizer = CremePoTokenizer(html)
        self.assertTrue(tokenizer.looks_like_html(html), f"Text was: {html}")
        tokenizer.preprocess_text()
        self.assertEqual(expected, tokenizer._text, f"Text was: {html}")

    def test_init__array(self):
        text = array.array("u", "Hello")
        tokenizer = CremePoTokenizer(text)
        self.assertEqual(tokenizer._text, "Hello")

    def test_init__text(self):
        text = "Hello"
        tokenizer = CremePoTokenizer(text)
        self.assertEqual(tokenizer._text, text)

    def test_preprocess_text_01(self):
        self.assertTokenizedTextEqual("Hello", ["Hello"])

    def test_preprocess_text_02(self):
        self.assertTokenizedTextEqual("Hello {first_name} {last_name}", ["Hello"])

    def test_preprocess_text_03(self):
        self.assertTokenizedTextEqual("Hello {user.name}", ["Hello"])

    def test_preprocess_text_04(self):
        self.assertTokenizedTextEqual("Hello %(name)s", ["Hello"])

    def test_preprocess_text_05(self):
        self.assertTokenizedTextEqual("Hello; Joe;", ["Hello", "Joe"])

    def test_preprocess_text_06(self):
        self.assertTokenizedTextEqual("Hello, Joe,", ["Hello", "Joe"])

    def test_preprocess_text_07(self):
        self.assertTokenizedTextEqual("Hello.Joe.", ["Hello", "Joe"])

    def test_preprocess_text_08(self):
        self.assertTokenizedTextEqual("Hello:Joe:", ["Hello", "Joe"])

    def test_preprocess_text_09(self):
        self.assertTokenizedTextEqual(" Hello Joe ", ["Hello", "Joe"])

    def test_preprocess_text_10(self):
        self.assertTokenizedTextEqual("«Hello» «Joe»", ["Hello", "Joe"])

    def test_preprocess_text_11(self):
        self.assertTokenizedTextEqual("Hello((Joe))", ["Hello", "Joe"])

    def test_preprocess_text_12(self):
        self.assertTokenizedTextEqual("Hello[[Joe]]", ["Hello", "Joe"])

    def test_preprocess_text_13(self):
        self.assertTokenizedTextEqual('Hello""Joe""', ["Hello", "Joe"])

    def test_preprocess_text_14(self):
        self.assertTokenizedTextEqual('Hello/Joe/', ["Hello", "Joe"])

    def test_preprocess_text_15(self):
        self.assertTokenizedTextEqual('Hello!Joe!', ["Hello", "Joe"])

    def test_preprocess_text_16(self):
        self.assertTokenizedTextEqual('Hello?Joe?', ["Hello", "Joe"])

    def test_preprocess_text_17(self):
        self.assertTokenizedTextEqual('Hello…Joe…', ["Hello", "Joe"])

    def test_preprocess_text_18(self):
        self.assertTokenizedTextEqual('Hello Joe (in %)', ["Hello", "Joe", "in"])

    def test_preprocess_text_19(self):
        self.assertTokenizedTextEqual('Hello=Joe', ["Hello", "Joe"])

    def test_preprocess_text_20(self):
        self.assertTokenizedTextEqual('Hello—Joe', ["Hello", "Joe"])

    def test_preprocess_text_21(self):
        self.assertTokenizedTextEqual("Hello'Joe'", ["Hello", "Joe"])

    def test_preprocess_html_01(self):
        self.assertTokenizedHtmlEqual('Hello Joe</br>', ["Hello", "Joe"])

    def test_preprocess_html_02(self):
        self.assertTokenizedHtmlEqual('<div>Hello Joe</div>', ["Hello", "Joe"])

    def test_preprocess_html_03(self):
        # TODO: title attribute too ?
        self.assertTokenizedHtmlEqual('Hello <strong>Joe</strong>', ["Hello", "Joe"])

    def test_regression_01(self):
        self.assertTokenizedTextEqual(
            "There is a connection error with the job manager.\n"
            "Please contact your administrator.\n"
            "[Original error from «{queue}»:\n"
            "{message}]",
            [
                "There", "is", "a", "connection", "error", "with", "the", "job",
                "manager", "Please", "contact", "your", "administrator",
                "Original", "error", "from"
            ]
        )

    def test_regression_02(self):
        self.assertTokenizedTextEqual(
            "Liste de choix multiples ({choices}) (supprimé(s) : {del_choices})",
            ["Liste", "de", "choix", "multiples", "supprimé", "s"])
