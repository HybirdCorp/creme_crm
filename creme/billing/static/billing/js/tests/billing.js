(function($) {

QUnit.module("creme.billing", new QUnitMixin(QUnitEventMixin,
                                             QUnitAjaxMixin,
                                             QUnitDialogMixin, {
    beforeEach: function() {}
}));

QUnit.test('creme.billing.checkPositiveDecimal', function(assert) {
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("text")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("true")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("false")));

    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("1")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123")));

    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.0")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.1")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.12")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("0.123")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.4")));
    assert.equal(true, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.45")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("123.456")));

    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.0")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.1")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.12")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-0.123")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.4")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.45")));
    assert.equal(false, creme.billing.checkPositiveDecimal($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkPositiveInteger', function(assert) {
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("text")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("true")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("false")));

    assert.equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("0")));
    assert.equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("1")));
    assert.equal(true, creme.billing.checkPositiveInteger($('<input type="text">').val("123")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123")));

    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.0")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.1")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.12")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("0.123")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.4")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.45")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("123.456")));

    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.0")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.1")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.12")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-0.123")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.4")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.45")));
    assert.equal(false, creme.billing.checkPositiveInteger($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkDecimal', function(assert) {
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("text")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("true")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("false")));

    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("0")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("1")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("123")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123")));

    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.0")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.1")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("0.12")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("0.123")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("123.4")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("123.45")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("123.456")));

    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.0")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.1")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-0.12")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("-0.123")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123.4")));
    assert.equal(true, creme.billing.checkDecimal($('<input type="text">').val("-123.45")));
    assert.equal(false, creme.billing.checkDecimal($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkPercent', function(assert) {
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("text")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("true")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("false")));

    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("0")));
    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("1")));
    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("100")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("123")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-0")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-123")));

    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("0.0")));
    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("0.1")));
    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("0.12")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("0.123")));

    assert.equal(true, creme.billing.checkPercent($('<input type="text">').val("100.0")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("100.01")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("100.1")));

    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("123.4")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("123.45")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("123.456")));

    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.0")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.1")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.12")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-0.123")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.4")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.45")));
    assert.equal(false, creme.billing.checkPercent($('<input type="text">').val("-123.456")));
});

QUnit.test('creme.billing.checkValue', function(assert) {
    assert.equal(false, creme.billing.checkValue($('<input type="text">').val("")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("text")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("true")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("false"))); // WTF ?

    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("0"))); // WTF ?
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("1")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("123")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("-0")));
    assert.equal(true, creme.billing.checkValue($('<input type="text">').val("-123")));
});

QUnit.test('creme.billing.validateInput', function(assert) {
    assert.equal(true, creme.billing.validateInput($('<input type="text" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="unknown" />')));

    assert.equal(false, creme.billing.validateInput($('<input validator="PositiveDecimal" />')));
    assert.equal(false, creme.billing.validateInput($('<input validator="PositiveDecimal" value="-1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="PositiveDecimal" value="1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="PositiveDecimal" value="0" />')));

    assert.equal(false, creme.billing.validateInput($('<input validator="Decimal" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Decimal" value="-1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Decimal" value="1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Decimal" value="0" />')));

    assert.equal(false, creme.billing.validateInput($('<input validator="Percent" />')));
    assert.equal(false, creme.billing.validateInput($('<input validator="Percent" value="-1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Percent" value="1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Percent" value="0" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Percent" value="100" />')));
    assert.equal(false, creme.billing.validateInput($('<input validator="Percent" value="100.5" />')));

    assert.equal(false, creme.billing.validateInput($('<input validator="Value" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Value" value="-1.5" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Value" value="text" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Value" value="false" />')));
    assert.equal(true, creme.billing.validateInput($('<input validator="Value" value="100" />')));
});

QUnit.test('creme.billing.markDelete', function(assert) {
    $(
        '<form>' +
            '<table><tr><td id="line_content_line-0">' +
                '<input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE" />' +
            '</td></tr>' +
            '<tr><td id="line_content_line-1" class="bline-deletion-mark">' +
                '<input type="checkbox" name="form-1-DELETE" id="id_form-1-DELETE" checked="checked"/>' +
            '</td></tr></table>' +
        '</form>'
    ).appendTo(this.qunitFixture());

    assert.equal($('#line_content_line-0').is('.bline-deletion-mark'), false);
    assert.equal($('#id_form-0-DELETE').prop('checked'), false);

    assert.equal($('#line_content_line-1').is('.bline-deletion-mark'), true);
    assert.equal($('#id_form-1-DELETE').prop('checked'), true);

    creme.billing.markDelete('form-0', 'line-0');
    creme.billing.markDelete('form-1', 'line-1');

    assert.equal($('#line_content_line-0').is('.bline-deletion-mark'), true);
    assert.equal($('#id_form-0-DELETE').prop('checked'), true);

    assert.equal($('#line_content_line-1').is('.bline-deletion-mark'), false);
    assert.equal($('#id_form-1-DELETE').prop('checked'), false);

    creme.billing.markDelete('form-0', 'line-0');
    creme.billing.markDelete('form-1', 'line-1');

    assert.equal($('#line_content_line-0').is('.bline-deletion-mark'), false);
    assert.equal($('#id_form-0-DELETE').prop('checked'), false);

    assert.equal($('#line_content_line-1').is('.bline-deletion-mark'), true);
    assert.equal($('#id_form-1-DELETE').prop('checked'), true);
});

QUnit.parametrize('creme.billing.checkDiscount', [
    [{discountUnit: '1', discount: 0, unitPrice: 0, quantity: 0}, true],
    [{discountUnit: '1', discount: 50, unitPrice: 10, quantity: 1}, true],
    [{discountUnit: '1', discount: 120, unitPrice: 0, quantity: 0}, false],
    [{discountUnit: '1', discount: -1, unitPrice: 0, quantity: 0}, false],

    [{discountUnit: '2', discount: 20, unitPrice: 10, quantity: 5}, true],
    [{discountUnit: '2', discount: 20, unitPrice: 10, quantity: 2}, true],
    [{discountUnit: '2', discount: 20, unitPrice: 10, quantity: 1}, false],

    [{discountUnit: '3', discount: 20, unitPrice: 30, quantity: 5}, true],
    [{discountUnit: '3', discount: 20, unitPrice: 20, quantity: 5}, true],
    [{discountUnit: '3', discount: 20, unitPrice: 10, quantity: 5}, false],

    [{discountUnit: 'invalid', discount: 0, unitPrice: 0, quantity: 0}, false]
], function(initial, expected, assert) {
    var element = $(
        '<form>' +
            '<table><tr><td id="line_content_line-0">' +
                '<select name="form-0-discount_unit">' +
                    '<option value="1">percent</option>' +
                    '<option value="2">line amount</option>' +
                    '<option value="3">item amount</option>' +
                    '<option value="invalid">invalid</option>' +
                '</select>' +
                '<input name="form-0-discount" />' +
                '<input name="form-0-unit_price" />' +
                '<input name="form-0-quantity" />' +
            '</td></tr>' +
            '</table>' +
        '</form>'
    ).appendTo(this.qunitFixture());

    element.find('select[name="form-0-discount_unit"]').val(initial.discountUnit);
    element.find('input[name="form-0-discount"]').val(initial.discount);
    element.find('input[name="form-0-unit_price"]').val(initial.unitPrice);
    element.find('input[name="form-0-quantity"]').val(initial.quantity);

    assert.equal(creme.billing.checkDiscount(element.find('[name="form-0-discount"]')), expected);
});

QUnit.parametrize('creme.billing.restoreValue', [
    ['<input name="a" value="12">', {key: 'a', value: '12'}, {key: 'a', value: ''}],
    ['<input name="a" value="12" initial="3">', {key: 'a', value: '12'}, {key: 'a', value: '3'}],
    ['<input name="a" type="checkbox" value="12">', undefined, undefined],
    ['<input name="a" type="checkbox" checked="checked" value="12">', {key: 'a', value: '12'}, undefined],
    ['<input name="a" type="checkbox" checked="checked" value="12" initial>', {key: 'a', value: '12'}, {key: 'a', value: '12'}]
], function(input, expected, restored, assert) {
    input = $(input);
    input.on('change', this.mockListener('change'));

    assert.deepEqual(creme.billing.serializeInput(input), expected);
    assert.equal(this.mockListenerCalls('change').length, 0);

    creme.billing.restoreValue(input);

    assert.deepEqual(creme.billing.serializeInput(input), restored);
    assert.equal(this.mockListenerCalls('change').length, 1);
});

QUnit.test('creme.billing.restoreInitialValues', function(assert) {
    var element = $(
        '<form>' +
            '<div class="bline-form">' +
                '<div class="bline-container">' +
                    '<div class="bline-buttons" id="line_content_line-0">' +
                        '<input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE" />' +
                    '</div>' +
                    '<div class="bline-hidden-fields"></div>' +
                    '<div class="bline-fields restorable_line-0">' +
                        '<table class="linetable"><tbody><tr class="content" data-row-index="0">' +
                            '<input type="checkbox" name="form-0-enabled" id="id_form-0-enabled" initial="1"/>' +
                            '<input name="form-0-unit_price" id="id_form-0-unit_price" initial="12.5" value="5.12"/>' +
                            '<input name="form-0-quantity" id="id_form-0-quantity" initial="5" value="18" />' +
                        '</td></tr></table>' +
                    '</div>' +
                '</div>' +
                '<div class="bline-container">' +
                    '<div class="bline-buttons bline-deletion-mark" id="line_content_line-1">' +
                        '<input type="checkbox" name="form-1-DELETE" id="id_form-1-DELETE" checked="checked"/>' +
                    '</div>' +
                    '<div class="bline-hidden-fields"></div>' +
                    '<div class="bline-fields restorable_line-1">' +
                        '<table class="linetable"><tbody><tr class="content" data-row-index="1">' +
                            '<input type="checkbox" name="form-1-enabled" id="id_form-1-enabled" checked="checked"/>' +
                            '<input name="form-1-unit_price" id="id_form-1-unit_price"  initial="2.5" value="5.12"/>' +
                            '<input name="form-1-quantity" id="id_form-1-quantity"  initial="7" value="18" />' +
                        '</td></tr></table>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</form>'
    ).appendTo(this.qunitFixture());

    assert.equal(element.find('[name="form-0-DELETE"]').prop('checked'), false);
    assert.equal(element.find('[name="form-0-enabled"]').prop('checked'), false);
    assert.equal(element.find('[name="form-0-unit_price"]').val(), '5.12');
    assert.equal(element.find('[name="form-0-quantity"]').val(), '18');

    assert.equal(element.find('[name="form-1-DELETE"]').prop('checked'), true);
    assert.equal(element.find('[name="form-1-enabled"]').prop('checked'), true);
    assert.equal(element.find('[name="form-1-unit_price"]').val(), '5.12');
    assert.equal(element.find('[name="form-1-quantity"]').val(), '18');

    creme.billing.restoreInitialValues('line-0', 'form-0');

    this.assertOpenedDialog(gettext('Do you really want to restore initial values of this line?'));
    this.acceptConfirmDialog();

    assert.equal(element.find('[name="form-0-DELETE"]').prop('checked'), false);
    assert.equal(element.find('[name="form-0-enabled"]').prop('checked'), true);
    assert.equal(element.find('[name="form-0-unit_price"]').val(), '12.5');
    assert.equal(element.find('[name="form-0-quantity"]').val(), '5');

    assert.equal(element.find('[name="form-1-DELETE"]').prop('checked'), true);
    assert.equal(element.find('[name="form-1-enabled"]').prop('checked'), true);
    assert.equal(element.find('[name="form-1-unit_price"]').val(), '5.12');
    assert.equal(element.find('[name="form-1-quantity"]').val(), '18');

    assert.equal(element.find('#line_content_line-1').is('.block_header_line_dark'), false);
    assert.equal(element.find('#line_content_line-1').is('.bline-deletion-mark'), true);

    creme.billing.restoreInitialValues('line-1', 'form-1');

    this.assertOpenedDialog(gettext('Do you really want to restore initial values of this line?'));
    this.acceptConfirmDialog();

    assert.equal(element.find('[name="form-0-DELETE"]').prop('checked'), false);
    assert.equal(element.find('[name="form-0-enabled"]').prop('checked'), true);
    assert.equal(element.find('[name="form-0-unit_price"]').val(), '12.5');
    assert.equal(element.find('[name="form-0-quantity"]').val(), '5');

    assert.equal(element.find('[name="form-1-DELETE"]').prop('checked'), false);
    assert.equal(element.find('[name="form-1-enabled"]').prop('checked'), false);
    assert.equal(element.find('[name="form-1-unit_price"]').val(), '2.5');
    assert.equal(element.find('[name="form-1-quantity"]').val(), '7');

    assert.equal(element.find('#line_content_line-1').is('.block_header_line_dark'), true);
    assert.equal(element.find('#line_content_line-1').is('.bline-deletion-mark'), false);
});

QUnit.parametrize('creme.billing.serializeInput', [
    ['<input />', undefined],
    ['<input value="12" />', undefined],
    ['<input initial="3"/>', undefined],
    ['<input value="12" initial="3"/>', undefined],
    ['<input name="a" type="checkbox" checked="checked" value="12"/>', {key: 'a', value: '12'}],
    ['<input name="a" type="checkbox" checked="checked" value="12" initial="3"/>', {key: 'a', value: '12'}]
], function(input, expected, assert) {
    assert.deepEqual(creme.billing.serializeInput($(input)), expected);
});

QUnit.parametrize('creme.billing.initBoundedFields', [
    [{}, {totalNoTax: 463.50, totalDiscounted: 454.23, total: 545.08}],
    [{quantity: 5}, {totalNoTax: 77.25, totalDiscounted: 75.71, total: 90.85}],
    [{unit_price: 5.45}, {totalNoTax: 163.50, totalDiscounted: 160.23, total: 192.28}],
    [{discount: 10.0}, {totalNoTax: 463.50, totalDiscounted: 417.15, total: 500.58}],
    [{discount_unit: 3}, {totalNoTax: 463.50, totalDiscounted: 403.50, total: 484.20}],
    [{discount_unit: 2}, {totalNoTax: 463.50, totalDiscounted: 461.50, total: 553.80}],
    [{vat_value: 5}, {totalNoTax: 463.50, totalDiscounted: 454.23, total: 550.53}],

    [{quantity: 'NaN'}, {totalNoTax: null, totalDiscounted: null, total: null}],
    [{quantity: -10}, {totalNoTax: null, totalDiscounted: null, total: null}],
    [{unit_price: 'NaN'}, {totalNoTax: null, totalDiscounted: null, total: null}],
    [{discount: 200.0}, {totalNoTax: null, totalDiscounted: null, total: null}],
    [{discount: -50.0}, {totalNoTax: null, totalDiscounted: null, total: null}],
    [{discount_unit: 'invalid'}, {totalNoTax: null, totalDiscounted: null, total: null}],

    [{vat_value: ''}, {totalNoTax: 463.50, totalDiscounted: 454.23, total: null}]
], function(changes, expected, assert) {
    var element = $(
        '<form>' +
            '<div class="bline-form">' +
                '<div class="bline-container">' +
                    '<div class="bline-buttons"></div>' +
                    '<div class="bline-hidden-fields"></div>' +
                    '<div class="bline-fields">' +
                        '<table class="linetable"><tbody><tr class="content" data-row-index="0">' +
                             '<td>' +
                                 '<input name="form-0-quantity" class="bound" validator="PositiveDecimal" value="30.00"/>' +
                                 '<input name="form-0-unit_price" class="bound" validator="Decimal" value="15.45"/>' +
                                 '<select name="form-0-discount_unit" class="bound">' +
                                     '<option value="1" selected="selected">percent</option>' +
                                     '<option value="2">line amount</option>' +
                                     '<option value="3">item amount</option>' +
                                     '<option value="invalid">invalid</option>' +
                                 '</select>' +
                                 '<input name="form-0-discount" class="bound" value="2" />' +
                                 '<select name="form-0-vat_value" class="bound">' +
                                     '<option value="">---</option>' +
                                     '<option value="6" selected="selected">20.00</option>' +
                                     '<option value="5">21.20</option>' +
                                 '</select>' +
                             '</td>' +
                             '<td class="bline-total-no-tax" name="exclusive_of_tax">463,50 €</td>' +
                             '<td class="bline-total-discounted" name="discounted" data-value="454.23">454,23 €</td>' +
                             '<td class="bline-total" name="inclusive_of_tax" data-value="545.08">545,08 €</td>' +
                         '</tr></tbody></table>' +
                     '</div>' +
                 '</div>' +
             '</div>' +
        '</form>'
    ).appendTo(this.qunitFixture());

    function formatAmount(amount) {
        if (Object.isNone(amount) || isNaN(amount)) {
            return '###';
        } else {
            return amount.toFixed(2).replace(".", ",") + " €";
        }
    };

    assert.equal('12,53 €', formatAmount(12.531));
    assert.equal('###', formatAmount(null));

    assert.deepEqual({
        totalNoTax: element.find('.bline-total-no-tax').text(),
        totalDiscounted: element.find('.bline-total-discounted').text(),
        total: element.find('.bline-total').text()
    }, {
        totalNoTax: formatAmount(463.50),
        totalDiscounted: formatAmount(454.23),
        total: formatAmount(545.08)
    });

    creme.billing.initBoundedFields(element.find('.linetable'), '€', 0.0);

    for (var name in changes) {
        var input = element.find('[name="form-0-${name}"]'.template({name: name}));
        input.val(changes[name]).trigger('change');
    }

    assert.deepEqual({
        totalNoTax: element.find('.bline-total-no-tax').text(),
        totalDiscounted: element.find('.bline-total-discounted').text(),
        total: element.find('.bline-total').text()
    }, {
        totalNoTax: formatAmount(expected.totalNoTax),
        totalDiscounted: formatAmount(expected.totalDiscounted),
        total: formatAmount(expected.total)
    });
});

QUnit.test('creme.billing.initializeForm (initial)', function(assert) {
    var element = $(
        '<form>' +
            '<div class="bline-form">' +
                '<div class="bline-container">' +
                    '<div class="bline-buttons"></div>' +
                    '<div class="bline-hidden-fields"></div>' +
                    '<div class="bline-fields">' +
                        '<table class="linetable"><tbody><tr class="content" data-row-index="0">' +
                             '<td>' +
                                 '<input name="form-0-quantity" class="bound" validator="PositiveDecimal" value="30.00"/>' +
                                 '<input name="form-0-unit_price" class="bound" validator="Decimal" value="15.45"/>' +
                                 '<select name="form-0-discount_unit" class="bound">' +
                                     '<option value="1" selected="selected">percent</option>' +
                                     '<option value="2">line amount</option>' +
                                     '<option value="3">item amount</option>' +
                                     '<option value="invalid">invalid</option>' +
                                 '</select>' +
                                 '<input name="form-0-discount" class="bound" value="2" />' +
                                 '<select name="form-0-vat_value" class="bound">' +
                                     '<option value="">---</option>' +
                                     '<option value="6" selected="selected">20.00</option>' +
                                     '<option value="5">21.20</option>' +
                                 '</select>' +
                             '</td>' +
                             '<td class="bline-total-no-tax" name="exclusive_of_tax">463,50 €</td>' +
                             '<td class="bline-total-discounted" name="discounted" data-value="454.23">454,23 €</td>' +
                             '<td class="bline-total" name="inclusive_of_tax" data-value="545.08">545,08 €</td>' +
                         '</tr></tbody></table>' +
                     '</div>' +
                 '</div>' +
             '</div>' +
        '</form>'
    ).appendTo(this.qunitFixture());

    creme.billing.initializeForm(element);

    assert.equal('30.00', element.find('[name="form-0-quantity"]').attr('initial'));
    assert.equal('15.45', element.find('[name="form-0-unit_price"]').attr('initial'));
    assert.equal('1', element.find('[name="form-0-discount_unit"]').attr('initial'));
    assert.equal('2', element.find('[name="form-0-discount"]').attr('initial'));
    assert.equal('6', element.find('[name="form-0-vat_value"]').attr('initial'));
});

}(jQuery));
