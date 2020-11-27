(function($) {

QUnit.module("creme.billing.orderline", new QUnitMixin(QUnitEventMixin,
                                                       QUnitAjaxMixin, {
    beforeEach: function() {
    },

    createOrderLineHtml: function(options) {
        options = options || {};
        return (
            '<form>' +
                '<input name="quantity" value="${quantity}"/>' +
                '<input name="unit_price" value="${unitPrice}"/>' +
                '<select name="unit">' +
                    '<option value="1" selected>Unit</option>' +
                    '<option value="2">Liter</option>' +
                '</select>' +
                '<input name="discount" value="${discountValue}" />' +
                '<select name="discount_unit">' +
                    '<option value="1">Percent</option>' +
                    '<option value="2">On line amount</option>' +
                    '<option value="3">On item amount</option>' +
                '</select>' +
                '<input name="vat_value" value="${taxRatio}"/>' +
                '<span name="discounted"></span>' +
                '<span name="inclusive_of_tax"></span>' +
                '<span name="exclusive_of_tax"></span>' +
            '</form>'
        ).template(function(key) {
            return options[key] || '';
        });
    }
}));

QUnit.test('creme.billing.OrderLine (defaults)', function(assert) {
    var element = $(this.createOrderLineHtml());
    var line = new creme.billing.OrderLine(element);

    equal(0.0, line.quantity());
    equal(0.0, line.unitPrice());
    equal('1', line.unit());
    equal(0.0, line.discountValue());
    equal(creme.billing.DiscountType.ITEM_PERCENT, line.discountUnit());
    equal(0.0, line.taxRatio());
    equal(0.0, line.totalNoTax());
    equal(0.0, line.total());

    line.clean();
    equal(false, line.isValid());

    equal('−', element.find('[name="discounted"]').text());
    equal('−', element.find('[name="inclusive_of_tax"]').text());
    equal('−', element.find('[name="exclusive_of_tax"]').text());
});

QUnit.test('creme.billing.OrderLine (no discount)', function(assert) {
    var element = $(this.createOrderLineHtml());
    var line = new creme.billing.OrderLine(element, {
        initial: {
            quantity: 5.0,
            unit_price: 10,
            vat_value: 0.2
        }
    });

    equal(5.0, line.quantity());
    equal(10, line.unitPrice());
    equal('1', line.unit());
    equal(0.0, line.discountValue());
    equal(creme.billing.DiscountType.ITEM_PERCENT, line.discountUnit());
    equal(0.2, line.taxRatio());
    equal(50.00, line.totalNoTax());
    equal(50.00, line.discountedTotalNoTax());
    equal(50.00 * 1.2, line.total());
    equal(50.00 * 1.2, line.discountedTotal());

    equal(true, line.isValid());

    equal('50.00 €', element.find('[name="discounted"]').text());
    equal('60.00 €', element.find('[name="inclusive_of_tax"]').text());
    equal('50.00 €', element.find('[name="exclusive_of_tax"]').text());
});

QUnit.parametrize('creme.billing.OrderLine (discount)', [
    [creme.billing.DiscountType.ITEM_PERCENT, 5.0, 47.50, 57.00],
    [creme.billing.DiscountType.ITEM_AMOUNT, 5.0, 25.00, 30.00],
    [creme.billing.DiscountType.LINE_AMOUNT, 5.0, 45.00, 54.00]
], function(discountType, discountValue, totalNoTax, total, assert) {
    var element = $(this.createOrderLineHtml());
    var line = new creme.billing.OrderLine(element, {
        initial: {
            quantity: 5.0,
            unit_price: 10,
            vat_value: 0.2,
            discount: discountValue,
            discount_unit: discountType
        }
    });

    equal(5.0, line.quantity());
    equal(10, line.unitPrice());
    equal('1', line.unit());
    equal(discountValue, line.discountValue());
    equal(discountType, line.discountUnit());
    equal(0.2, line.taxRatio());

    line.clean();
    equal(true, line.isValid());

    equal(totalNoTax, line.discountedTotalNoTax());
    equal(total, line.discountedTotal());

    equal(50.00, line.totalNoTax());
    equal(60.00, line.total());

    equal(totalNoTax.toFixed(2) + ' €', element.find('[name="discounted"]').text());
    equal('60.00 €', element.find('[name="inclusive_of_tax"]').text());
    equal('50.00 €', element.find('[name="exclusive_of_tax"]').text());
});

QUnit.parametrize('creme.billing.OrderLine (invalid discounts)', [
    [creme.billing.DiscountType.ITEM_PERCENT, -5.0, false, {
        code: 'rangeUnderflow',
        message: gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.ITEM_PERCENT, -0.01, false, {
        code: 'rangeUnderflow',
        message: gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.ITEM_PERCENT, 0, true],
    [creme.billing.DiscountType.ITEM_PERCENT, 100.0, true],
    [creme.billing.DiscountType.ITEM_PERCENT, 100.01, false, {
        code: 'rangeOverflow',
        message: gettext("This value must be inferior or equal to 100")
    }],

    [creme.billing.DiscountType.ITEM_AMOUNT, -5.0, false, {
        code: 'rangeUnderflow',
        message: gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.ITEM_AMOUNT, -0.01, false, {
        code: 'rangeUnderflow',
        message:  gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.ITEM_AMOUNT, 0, true],
    [creme.billing.DiscountType.ITEM_AMOUNT, 9.80, true],
    [creme.billing.DiscountType.ITEM_AMOUNT, 9.81, false, {
        code: 'rangeOverflow',
        message: gettext("This value must be inferior or equal to 9.8")
    }],

    [creme.billing.DiscountType.LINE_AMOUNT, -5.0, false, {
        code: 'rangeUnderflow',
        message: gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.LINE_AMOUNT, -0.01, false, {
        code: 'rangeUnderflow',
        message: gettext("This value must be superior or equal to 0")
    }],
    [creme.billing.DiscountType.LINE_AMOUNT, 0, true],
    [creme.billing.DiscountType.LINE_AMOUNT, 49.0, true],
    [creme.billing.DiscountType.LINE_AMOUNT, 49.01, false, {
        code: 'rangeOverflow',
        message: gettext("This value must be inferior or equal to 49")
    }]
], function(discountType, discountValue, isValid, errorMessage, assert) {
    var element = $(this.createOrderLineHtml());
    var line = new creme.billing.OrderLine(element, {
        initial: {
            quantity: 5.0,
            unit_price: 9.80,
            vat_value: 0.2,
            discount: discountValue,
            discount_unit: discountType
        }
    });

    equal(5.0, line.quantity());
    equal(9.80, line.unitPrice());
    equal('1', line.unit());
    equal(discountValue, line.discountValue());
    equal(discountType, line.discountUnit());
    equal(0.2, line.taxRatio());

    var output = line.clean();
    equal(isValid, output.isValid);

    if (!isValid) {
        deepEqual({
            discount: errorMessage
        }, output.fieldErrors);
    }
});

}(jQuery));
