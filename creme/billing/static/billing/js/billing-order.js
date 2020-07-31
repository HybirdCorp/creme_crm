(function($) {
"use strict";

var __DiscountType = {
    ITEM_PERCENT: 1,
    LINE_AMOUNT: 2,
    ITEM_AMOUNT: 3
};

function __assertDiscountType(value) {
    Assert.in(value, Object.values(__DiscountType), "${value} is not a discount type");
}

function __decimalConstraint(min, max) {
    return function(value) {
        if (value < min) {
            throw new creme.form.ValidationError('rangeUnderflow');
        } else if (!isNaN(max) && value > max) {
            throw new creme.form.ValidationError('rangeOverflow');
        }
    };
}

function __fixed(precision) {
    return function(value, field) {
        if (!field.required() && Object.isEmpty(value)) {
            return;
        }

        value = Object.isString(value) ? parseFloat(value) : value;
        Assert.not(isNaN(value), "${value} is not a number", {value: value});
        return value ? Math.scaleRound(value, precision) : value;
    };
}

creme.billing.DiscountType = $.extend({}, __DiscountType);

creme.billing.OrderLine = creme.component.Component.sub({
    _init_: function(element, options) {
        options = $.extend({
            currencyFormat: '${amount} €'
        }, options || {});

        this.currency(options.currency);

        this._element = $(element);
        this._form = element.flyform({
            responsive: true,
            fields: {
                quantity: {
                    dataType: 'decimal',
                    required: true,
                    constraints: __decimalConstraint(0),
                    parser: __fixed(2)
                },
                unit_price: {
                    dataType: 'decimal',
                    required: true,
                    constraints: __decimalConstraint(0),
                    parser: __fixed(3)
                },
                discount: {
                    dataType: 'decimal',
                    constraints: __decimalConstraint(0),
                    parser: __fixed(2)
                },
                discount_unit: {
                    dataType: 'integer',
                    constraints: __assertDiscountType
                },
                vat_value: {
                    dataType: 'decimal',
                    constraints: __decimalConstraint(0, 1),
                    parser: __fixed(3)
                }
            }
        });

        this._element.on('form-clean', this._onFormClean.bind(this));

        if (options.initial) {
            this._form.initialData(options.initial).reset();
        }
    },

    element: function() {
        return this._element;
    },

    form: function() {
        return this._form;
    },

    _formatAmount: function(value) {
        return Object.isEmpty(value) ? '−' : (this.currencyFormat() || '').template({
            amount: value.toFixed(2)
        });
    },

    _onFormClean: function(event, form, output) {
        var element = this.element();

        if (output.isValid) {
            $.extend(output.cleanedData, {
                discountedNoTax: this.discountedTotalNoTax(),
                total: this.total(),
                totalNoTax: this.totalNoTax()
            });
        }

        var data = output.cleanedData;
        element.find('[name="discounted"]').text(this._formatAmount(data.discountedNoTax));
        element.find('[name="inclusive_of_tax"]').text(this._formatAmount(data.total));
        element.find('[name="exclusive_of_tax"]').text(this._formatAmount(data.totalNoTax));

        if (output.isValid) {
            element.trigger('orderline-change', data);
        }
    },

    clean: function() {
        this._form.clean({noThrow: true});
        return this;
    },

    currencyFormat: function(format) {
        Object.property(this, '_currencyFormat', format);
    },

    field: function(name) {
        return this._form.field(name);
    },

    quantity: function() {
        return this.field('quantity').clean({noThrow: true}) || 0.0;
    },

    unitPrice: function() {
        return this.field('unit_price').clean({noThrow: true}) || 0.0;
    },

    unit: function() {
        return this.field('unit').clean({noThrow: true});
    },

    discountUnit: function() {
        return this.field('discount_unit').clean({noThrow: true}) || __DiscountType.ITEM_PERCENT;
    },

    discountValue: function() {
        return this.field('discount').clean({noThrow: true}) || 0.0;
    },

    taxRatio: function() {
        // TODO : store the ratio in the <option> value directly !
        return this.field('vat_value').clean({noThrow: true}) || 0.0;
    },

    totalNoTax: function() {
        var quantity = this.quantity();
        var unitPrice = this.unitPrice();

        return Math.scaleRound(quantity * unitPrice, 2);
    },

    discountedTotalNoTax: function() {
        var quantity = this.quantity();
        var unitPrice = this.unitPrice();
        var discount = this.discountValue();
        var discountUnit = this.discountUnit();
        var total = 0.0;

        switch (discountUnit) {
            case __DiscountType.LINE_AMOUNT:
                total = (quantity * unitPrice) - discount;
                break;
            case __DiscountType.ITEM_PERCENT:
                total = quantity * (unitPrice - (unitPrice * discount / 100));
                break;
            case __DiscountType.ITEM_AMOUNT:
                total = quantity * (unitPrice - discount);
                break;
            default:
                throw new Error('Invalid discount type "' + discountUnit + '"');
        }

        return Math.scaleRound(total, 2);
    },

    discountedTotal: function() {
        return this.discountedTotalNoTax() * (1.0 + this.taxRatio());
    },

    total: function() {
        return this.totalNoTax() * (1.0 + this.taxRatio());
    }
});

}(jQuery));
