(function($) {
"use strict";

var __DiscountType = {
    ITEM_PERCENT: 1,
    LINE_AMOUNT: 2,
    ITEM_AMOUNT: 3
};

function __checkDecimalRange(fieldname, value, min, max) {
    if (value < min) {
        throw new creme.form.ValidationError({
            field: fieldname,
            code: 'rangeUnderflow',
            message: gettext('This value must be superior or equal to ${min}'),
            min: min
        });
    } else if (!isNaN(max) && value > max) {
        throw new creme.form.ValidationError({
            field: fieldname,
            code: 'rangeOverflow',
            message: gettext('This value must be inferior or equal to ${max}'),
            max: max
        });
    }
}

function __discountValueConstraint(form, output) {
    var quantity = output.cleanedData.quantity;
    var unitPrice = output.cleanedData.unit_price;
    var discountUnit = output.cleanedData.discount_unit;
    var value = output.cleanedData.discount;

    switch (discountUnit) {
        case __DiscountType.LINE_AMOUNT:
            __checkDecimalRange('discount', value, 0, quantity * unitPrice);
            break;
        case __DiscountType.ITEM_PERCENT:
            __checkDecimalRange('discount', value, 0, 100);
            break;
        case __DiscountType.ITEM_AMOUNT:
            __checkDecimalRange('discount', value, 0, unitPrice);
            break;
        default:
            __checkDecimalRange('discount', value, 0);
    }
}

function __discountTypeConstraint(form, output) {
    var value = output.cleanedData.discount_unit;

    if (Object.values(__DiscountType).indexOf(value) === -1) {
        throw new creme.form.ValidationError({
            code: 'cleanMismatch',
            field: 'discount_unit',
            message: gettext('"${value}" is not a valid discount type'),
            value: value
        });
    }
}

function __decimalConstraint(field, min, max) {
    return function(form, data) {
        __checkDecimalRange(field, data[field], min, max);
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

        this.currencyFormat(options.currencyFormat);

        this._element = $(element);
        this._form = element.flyform({
            fields: {
                quantity: {
                    dataType: 'decimal',
                    required: true,
                    parser: __fixed(2)
                },
                unit_price: {
                    dataType: 'decimal',
                    required: true,
                    parser: __fixed(3)
                },
                discount: {
                    dataType: 'decimal',
                    parser: __fixed(2)
                },
                discount_unit: {
                    dataType: 'integer'
                },
                vat_value: {
                    dataType: 'decimal',
                    parser: __fixed(3)
                }
            },
            constraints: [
                __decimalConstraint('quantity', 0),
                __decimalConstraint('unit_price', 0),
                __decimalConstraint('vat_value', 0, 1),
                __discountTypeConstraint,
                __discountValueConstraint
            ]
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
        return Object.isEmpty(value) ? '−' : (this.currencyFormat() || '${amount}').template({
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
        return this._form.clean({noThrow: true});
    },

    currencyFormat: function(format) {
        return Object.property(this, '_currencyFormat', format);
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

    isValid: function() {
        return this._form.isValid();
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
                total = quantity * unitPrice;
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
