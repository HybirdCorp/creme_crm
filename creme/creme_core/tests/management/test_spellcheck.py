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

    def test_preprocess_text__simple(self):
        self.assertTokenizedTextEqual("Hello", ["Hello"])

    def test_preprocess_text__bracket_vars(self):
        self.assertTokenizedTextEqual("Hello {first_name} {last_name}", ["Hello"])

    def test_preprocess_text__bracket_vars__subfield(self):
        self.assertTokenizedTextEqual("Hello {user.name}", ["Hello"])

    def test_preprocess_text__percent_vars(self):
        self.assertTokenizedTextEqual("Hello %(name)s", ["Hello"])

    def test_preprocess_text__semi_colon(self):
        self.assertTokenizedTextEqual("Hello; Joe;", ["Hello", "Joe"])

    def test_preprocess_text__comma(self):
        self.assertTokenizedTextEqual("Hello, Joe,", ["Hello", "Joe"])

    def test_preprocess_text__period(self):
        self.assertTokenizedTextEqual("Hello.Joe.", ["Hello", "Joe"])

    def test_preprocess_text__colon(self):
        self.assertTokenizedTextEqual("Hello:Joe:", ["Hello", "Joe"])

    def test_preprocess_text__space(self):
        self.assertTokenizedTextEqual(" Hello Joe ", ["Hello", "Joe"])

    def test_preprocess_text__quotation_mark(self):
        self.assertTokenizedTextEqual("«Hello» «Joe»", ["Hello", "Joe"])

    def test_preprocess_text__parenthesis(self):
        self.assertTokenizedTextEqual("Hello((Joe))", ["Hello", "Joe"])

    def test_preprocess_text__square_bracket(self):
        self.assertTokenizedTextEqual("Hello[[Joe]]", ["Hello", "Joe"])

    def test_preprocess_text__quote(self):
        self.assertTokenizedTextEqual('Hello""Joe""', ["Hello", "Joe"])

    def test_preprocess_text__slash(self):
        self.assertTokenizedTextEqual('Hello/Joe/', ["Hello", "Joe"])

    def test_preprocess_text__exclamation(self):
        self.assertTokenizedTextEqual('Hello!Joe!', ["Hello", "Joe"])

    def test_preprocess_text__interrogation(self):
        self.assertTokenizedTextEqual('Hello?Joe?', ["Hello", "Joe"])

    def test_preprocess_text__ellipsis(self):
        self.assertTokenizedTextEqual('Hello…Joe…', ["Hello", "Joe"])

    def test_preprocess_text__percent(self):
        self.assertTokenizedTextEqual('Hello Joe (in %)', ["Hello", "Joe", "in"])

    def test_preprocess_text__equal(self):
        self.assertTokenizedTextEqual('Hello=Joe', ["Hello", "Joe"])

    def test_preprocess_text__hiphen(self):
        self.assertTokenizedTextEqual('Hello—Joe', ["Hello", "Joe"])

    def test_preprocess_text__simple_quote(self):
        self.assertTokenizedTextEqual("Hello'Joe'", ["Hello", "Joe"])

    def test_preprocess_html__br(self):
        self.assertTokenizedHtmlEqual('Hello Joe</br>', ["Hello", "Joe"])

    def test_preprocess_html__div(self):
        self.assertTokenizedHtmlEqual('<div>Hello Joe</div>', ["Hello", "Joe"])

    def test_preprocess_html__strong(self):
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
