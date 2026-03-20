(function($) {

QUnit.module("creme.billing", new QUnitMixin(QUnitEventMixin,
                                             QUnitAjaxMixin,
                                             QUnitDialogMixin,
                                             QUnitMouseMixin,
                                             QUnitBrickMixin, {
    createBillingLinesBrick: function(options) {
        var html = this.createBillingLinesBrickHtml(options);

        var element = $(html).appendTo(this.qunitFixture());
        var widget = creme.widget.create(element);
        var brick = widget.brick();

        this.assert.equal(true, brick.isBound());
        this.assert.equal(false, brick.isLoading());

        return widget;
    },

    createBillingLinesBrickHtml: function(options) {
        options = $.extend({
            id: 'orderlines-test',
            title: 'Test it',
            header: '',
            classes: ['billing-lines-brick'],
            deps: [],
            attributes: {
                "data-type-currency": "€",
                "data-type-global-discount": 0,
                "data-drag-start-delay": 0,
                "data-revert-delay": 0
            }
        }, options || {});

        var lines = _.pop(options, 'lines') || [];

        options['content'] = '<div class="bline-form ui-sortable">${form}${lines}</div>'.template({
            lines: lines.map(this.createOrderLineHtml.bind(this)).join(''),
            form: (
                '<input type="hidden" name="csrfmiddlewaretoken">' +
                '<input type="hidden" name="line_formset-TOTAL_FORMS" value="${count}" id="id_line_formset-TOTAL_FORMS" initial="${count}">' +
                '<input type="hidden" name="line_formset-INITIAL_FORMS" value="${count}" id="id_line_formset-INITIAL_FORMS" initial="${count}">' +
                '<input type="hidden" name="line_formset-MIN_NUM_FORMS" value="0" id="id_line_formset-MIN_NUM_FORMS" initial="0">' +
                '<input type="hidden" name="line_formset-MAX_NUM_FORMS" value="1000" id="id_line_formset-MAX_NUM_FORMS" initial="1000">'
            ).template({
                count: lines.length
            })
        });

        return this.createBrickHtml(options);
    },

    createOrderLineHtml: function(options) {
        options = Object.assign({
            index: 0,
            discountUnitOptions: [
                {value: 1, name: 'percent'},
                {value: 2, name: 'line amount'},
                {value: 3, name: 'item amount'}
            ],
            vatOptions: [
                {value: '', name: '-----'},
                {value: 1, name: '0.00 %'},
                {value: 3, name: '5.50 %'},
                {value: 4, name: '7.00 %'},
                {value: 2, name: '13.60 %'},
                {value: 6, name: '20.00 %'},
                {value: 5, name: '21.20 %'}
            ],
            enabled: false,
            unitPrice: 1,
            quantity: 1,
            deleted: false,
            vat: 6,
            totalNoVat: 1,
            totalDiscount: 0,
            total: 1,
            discountUnit: 1,
            discountValue: 0,
            reorderUrl: 'mock/brick/reorder',
            // HACK : The drag placeholder has a min height of 140px. If the lines are smaller, the
            // dragndrop simulation will (obviously) not work.
            minHeight: "140px"
        }, options || {});

        options['enabledChecked'] = options.enabled ? ' checked' : '';
        options['deletedChecked'] = options.deleted ? ' checked' : '';
        options['order'] = options.order || options.index;

        function renderOptions(items, selected) {
            return items.map(function(item) {
                '<option value="${value}" ${selected}>${name}</option>'.template({
                    value: item.value,
                    selected: item.value === selected ? 'selected="selected"' : '',
                    name: item.name
                });
            }).join('');
        }

        options['discountUnitOptionsHtml'] = renderOptions(options.discountUnitOptions, options.discountUnit);
        options['vatOptionsHtml'] = renderOptions(options.vatOptions, options.vat);

        return (
            '<div class="bline-container bline-sortable" data-bline-order="${order}" data-bline-reorder-url="${reorderUrl}" style="min-height: ${minHeight}">' +
                '<div class="bline-buttons" id="line_content_${index}">' +
                    '<span class="bline-counter">${index}</span>' +
                    '<input type="checkbox" name="form-${index}-DELETE" id="id_form-${index}-DELETE" ${deletedChecked}/>' +
                '</div>' +
                '<div class="bline-hidden-fields"></div>' +
                '<div class="bline-fields restorable_${index}">' +
                    '<table class="linetable"><tbody><tr class="content" data-row-index="0">' +
                        '<td>' +
                            '<input type="checkbox" name="form-${index}-enabled" id="id_form-0-enabled" ${enabledChecked}/>' +
                            '<input name="form-${index}-unit_price" id="id_form-${index}-unit_price" class="bound" validator="PositiveDecimal" value="${unitPrice}"/>' +
                            '<input name="form-${index}-quantity" id="id_form-${index}-quantity" class="bound" validator="Decimal" value="${quantity}" />' +
                            '<select name="form-${index}-discount_unit" class="bound">${discountUnitOptionsHtml}</select>' +
                            '<input name="form-${index}-discount" class="bound" value="${discountValue}" />' +
                            '<select name="form-${index}-vat_value" class="bound">${vatOptionsHtml}</select>' +
                        '</td>' +
                        '<td class="bline-total-no-tax" name="exclusive_of_tax">${totalNoVat}</td>' +
                        '<td class="bline-total-discounted" name="discounted" data-value="${totalDiscount}">${totalDiscount}</td>' +
                        '<td class="bline-total" name="inclusive_of_tax" data-value="${total}">${total}</td>' +
                    '</td></tr></table>' +
                '</div>' +
                '<div class="bline-reorder-anchor ui-sortable-handle">#</div>' +
            '</div>'
        ).template(options);
    }
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


QUnit.test('creme.billing.BillingLinesBrick (reorder simple swap)', function(assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, order: 4},
            {index: 1, order: 6}
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order="4"] .bline-reorder-anchor');
    var target = element.find('[data-bline-order="6"]');

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual([
                ['POST', {target: 6}]
            ], this.mockBackendUrlCalls('mock/brick/reorder'));
            assert.deepEqual([
                ['GET', {"brick_id": ["orderlines-test"], "extra_data": "{}"}]
            ], this.mockBackendUrlCalls('mock/brick/all/reload'));

            this.assertClosedDialog();
        }
    );
});

QUnit.test('creme.billing.BillingLinesBrick (reorder simple swap, backward)', function(assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, order: 4},
            {index: 1, order: 6}
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order="6"] .bline-reorder-anchor');
    var target = element.find('[data-bline-order="4"]');

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual([
                ['POST', {target: 4}]
            ], this.mockBackendUrlCalls('mock/brick/reorder'));
            assert.deepEqual([
                ['GET', {"brick_id": ["orderlines-test"], "extra_data": "{}"}]
            ], this.mockBackendUrlCalls('mock/brick/all/reload'));

            this.assertClosedDialog();
        }
    );
});

QUnit.skipParametrizeIf(!QUnit.browsers.isHeadless() || QUnit.browsers.isChrome(), 'creme.billing.BillingLinesBrick (reorder usecases)', [
    [0, 2, [['POST', {target: 6}]]],  // 1
    [2, 0, [['POST', {target: 4}]]],  // 2
    [0, 3, [['POST', {target: 7}]]],  // 3
    [3, 0, [['POST', {target: 4}]]],  // 4
    [1, 2, [['POST', {target: 6}]]]   // 5
], function(from, to, expected, assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, order: 4},
            {index: 1, order: 5},
            {index: 2, order: 6},
            {index: 4, order: 7}
        ],
        minHeight: "124px"
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order]').eq(from).find('.bline-reorder-anchor');
    var target = element.find('[data-bline-order]').eq(to).find('.bline-reorder-anchor');

    // HACK : move the fixture element to (0,0) or the simulation will not work for an unknown reason.
    this.qunitFixture().css({top: 0, left: 0});

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual(expected, this.mockBackendUrlCalls('mock/brick/reorder'));

            if (expected.length > 0) {
                assert.deepEqual([
                    ['GET', {"brick_id": ["orderlines-test"], "extra_data": "{}"}]
                ], this.mockBackendUrlCalls('mock/brick/all/reload'));
            } else {
                assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
            }

            this.assertClosedDialog();
        }
    );
});


QUnit.skipParametrizeIf(!QUnit.browsers.isHeadless() || QUnit.browsers.isChrome(), 'creme.bricks.BillingLinesBrick (reorderable usecases, holes & repeats & other items)', [
    [0, 2, [['POST', {target: 6}]]],  // 1
    [2, 0, [['POST', {target: 3}]]],  // 2
    [0, 4, [['POST', {target: 7}]]],  // 3
    [4, 0, [['POST', {target: 3}]]],  // 4
    [1, 2, []],                       // 5
    [2, 2, []]                        // 6
], function(from, to, expected, assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, order: 3},
            {index: 1, order: 6},
            {index: 2, order: 6},
            {index: 3, order: "NaN", reorderUrl: ''},
            {index: 4, order: 7}
        ],
        minHeight: "124px"
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order]').eq(from).find('.bline-reorder-anchor');
    var target = element.find('[data-bline-order]').eq(to).find('.bline-reorder-anchor');

    // HACK : move the fixture element to (0,0) or the simulation will not work for an unknown reason.
    this.qunitFixture().css({top: 0, left: 0});

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual(expected, this.mockBackendUrlCalls('mock/brick/reorder'));

            if (expected.length > 0) {
                assert.deepEqual([
                    ['GET', {"brick_id": ["orderlines-test"], "extra_data": "{}"}]
                ], this.mockBackendUrlCalls('mock/brick/all/reload'));
            } else {
                assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
            }

            this.assertClosedDialog();
        }
    );
});


QUnit.test('creme.billing.BillingLinesBrick (reorder, invalid query)', function(assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, reorderUrl: 'mock/brick/reorder/fail'},
            {index: 1, reorderUrl: 'mock/brick/reorder/fail'}
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order="0"] .bline-reorder-anchor');
    var target = element.find('[data-bline-order="1"]');

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual([
                ['POST', {target: 1}]
            ], this.mockBackendUrlCalls('mock/brick/reorder/fail'));
            assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

            this.assertClosedDialog();
        }
    );
});

QUnit.test('creme.bricks.BillingLinesBrick (reorderable, invalid data)', function(assert) {
    var widget = this.createBillingLinesBrick({
        lines: [
            {index: 0, order: "0", reorderUrl: ''},
            {index: 1, order: "NaN", reorderUrl: 'mock/brick/reorder'}
        ]
    });

    var brick = widget.brick();
    var element = brick.element();

    assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    var source = element.find('[data-bline-order="0"] .bline-reorder-anchor');
    var target = element.find('[data-bline-order="NaN"]');

    this.awaits(
        this.simulateDragNDrop({
            source: source,
            target: target,
            dragStartDelay: 250,
            revertDelay: 250
        }),
        function() {
            assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/reorder'));
            assert.deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
            this.assertClosedDialog();
        }
    );
});

}(jQuery));
