(function($) {

QUnit.module("creme.billing", new QUnitMixin(QUnitEventMixin,
                                             QUnitAjaxMixin, {
    beforeEach: function() {}
}));

QUnit.test('creme.billing.checkPositiveDecimal', function(assert) {
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("text")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("true")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("false")));

    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("1")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123")));

    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.0")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.1")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.12")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.123")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.4")));
    equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.45")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.456")));

    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.0")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.1")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.12")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.123")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.4")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.45")));
    equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkPositiveInteger', function(assert) {
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("text")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("true")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("false")));

    equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("0")));
    equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("1")));
    equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("123")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123")));

    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.0")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.1")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.12")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.123")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.4")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.45")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.456")));

    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.0")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.1")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.12")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.123")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.4")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.45")));
    equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkDecimal', function(assert) {
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("text")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("true")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("false")));

    equal(true, creme.billing.checkDecimal($('<input type="text">').val("0")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("1")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("123")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123")));

    equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.0")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.1")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.12")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("0.123")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("123.4")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("123.45")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("123.456")));

    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.0")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.1")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.12")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("-0.123")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123.4")));
    equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123.45")));
    equal(false, creme.billing.checkDecimal($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkPercent', function(assert) {
    equal(false, creme.billing.checkPercent($('<input type="text">').val("")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("text")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("true")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("false")));

    equal(true, creme.billing.checkPercent($('<input type="text">').val("0")));
    equal(true, creme.billing.checkPercent($('<input type="text">').val("1")));
    equal(true, creme.billing.checkPercent($('<input type="text">').val("100")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("123")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-0")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-123")));

    equal(true, creme.billing.checkPercent($('<input type="text">').val("0.0")));
    equal(true, creme.billing.checkPercent($('<input type="text">').val("0.1")));
    equal(true, creme.billing.checkPercent($('<input type="text">').val("0.12")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("0.123")));

    equal(true, creme.billing.checkPercent($('<input type="text">').val("100.0")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("100.01")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("100.1")));

    equal(false, creme.billing.checkPercent($('<input type="text">').val("123.4")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("123.45")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("123.456")));

    equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.0")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.1")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.12")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.123")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.4")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.45")));
    equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkValue', function(assert) {
    equal(false, creme.billing.checkValue($('<input type="text">').val("")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("text")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("true")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("false"))); // WTF ?

    equal(true, creme.billing.checkValue($('<input type="text">').val("0"))); // WTF ?
    equal(true, creme.billing.checkValue($('<input type="text">').val("1")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("123")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("-0")));
    equal(true, creme.billing.checkValue($('<input type="text">').val("-123")));
});

}(jQuery));
