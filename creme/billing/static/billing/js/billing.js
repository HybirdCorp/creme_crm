/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*******************************************************************************/

/*
 * Requires : jQuery, Creme
 */

(function($) {
"use strict";

creme.billing = creme.billing || {};

// TODO: move most of these functions in core

creme.billing.checkPositiveDecimal = function(element) {
    return element.val().match(/^[0-9]+(\.[0-9]{1,2}){0,1}$/) !== null;
};

creme.billing.checkPositiveInteger = function(element) {
    return element.val().match(/^[0-9]+$/) !== null;
};

creme.billing.checkDecimal = function(element) {
    return element.val().match(/^[\-]{0,1}[0-9]+(\.[0-9]{1,2}){0,1}$/) !== null;
};

creme.billing.checkPercent = function(element) {
    // 100[.][0-99] or [0-99][.][0-99]
    return element.val().match(/^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/) !== null;
};

creme.billing.checkValue = function(element) {
    return Boolean(element.val());
};

creme.billing.checkDiscount = function(element) {
    var parent_tr      = element.closest('tr');
    var discount_unit  = parseInt($('select[name*=discount_unit]', parent_tr).val());
    var discount_value = parseFloat($('input[name*=discount]', parent_tr).val());
    var unit_price     = parseFloat($('input[name*=unit_price]', parent_tr).val());
    var quantity       = parseInt($('input[name*=quantity]', parent_tr).val());

    switch (discount_unit) {
        case 1: // DISCOUNT_PERCENT
            return creme.billing.checkPercent(element);

        case 2: // DISCOUNT_LINE_AMOUNT
            return discount_value <= unit_price * quantity;

        case 3: // DISCOUNT_ITEM_AMOUNT
            return discount_value <= unit_price;

        default:
            console.log("checkDiscount(): Bad discount value ?!", discount_unit);
    }

    return false;
};

creme.billing.markDelete = function(prefix, lineId) {
    var name = prefix + '-DELETE';
    var checkbox = $('#id_' + name);
    var line = $('#line_content_' + lineId);

    var toDelete = !checkbox.is(':checked');

    checkbox.prop('checked', toDelete);
    line.toggleClass('bline-deletion-mark', toDelete);

    // TODO: remove the id of <tbody> ??
//    var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
//    tbodyform.toggleClass('form_modified', to_delete);
};

creme.billing.inputs = function(element) {
    return $('input, select, textarea', element);
};

creme.billing.forms = function(element) {
    return $('.bline-form', element);
};

creme.billing.modifiedBLineForms = function() {
    return $('.bline-form').filter(function() {
        return Boolean(($('> :not(.hidden-form) .bline-input-modified, .bline-deletion-mark', $(this)).first().length));
    });
};

creme.billing.formsHaveErrors = function() {
    return Boolean($('.bline-form > :not(.hidden-form) .bline-input-error').first().length);
};

creme.billing.serializeInput = function(input) {
    var key = input.attr('name');
    var value = input.attr('type') === 'checkbox' ? (input.prop('checked') ? input.val() : undefined) : input.val();

    if (key !== undefined && value !== undefined) {
        return {key: key, value: value};
    }
};

creme.billing.validateInput = function(input) {
    var validator = input.attr('validator') ? creme.billing['check' + input.attr('validator')] : undefined;
    var isvalid = input.attr('isvalid') || false;

    if (Object.isFunc(validator)) {
        isvalid = validator(input);
    } else {
        isvalid = true;
    }

    input.attr('isvalid', isvalid);
    input.toggleClass('bline-input-error', !isvalid);

    return isvalid;
};

creme.billing.initializeForm = function(element) {
    creme.billing.inputs(element).each(function() {
        var input = $(this);
        var item = creme.billing.serializeInput(input);
        input.attr('initial', item !== undefined ? item.value : undefined);
        creme.billing.validateInput(input);
    });

    // Bind twice because of double init of blocks, seems to not cause a problem
    creme.billing.inputs(element).on('propertychange input change paste', function() {
        var input = $(this);
        var item = creme.billing.serializeInput(input);
        var changed = (item !== undefined && ('' + item.value !== input.attr('initial')));

        if (input.attr('type') === 'checkbox' && item === undefined && input.attr('initial')) {
            changed = true;
        }

        creme.billing.validateInput(input);
        input.toggleClass('bline-input-modified', changed);

        // TODO: we should also hide/show the buttonS (beware there are several bricks) to save the lines
        var lineContainer = input.closest('.bline-container');
        lineContainer.toggleClass(
            'bline-container-modified',
             lineContainer.has('.bline-input-modified')[0] !== undefined
        );
    });
};

creme.billing.initializeForms = function(element) {
    creme.billing.forms(element).each(function() {
        creme.billing.initializeForm($(this));
    });
};

creme.billing.hideEmptyForm = function(ct_id, formset_prefix, line_count) {
    $('.empty_form_' + ct_id).toggleClass('hidden-form', true);

    // Update total forms count
    var form_count_hidden_input = $('#id_' + formset_prefix + '-TOTAL_FORMS');
    form_count_hidden_input.val(parseInt(form_count_hidden_input.val()) - 1);

    // Show the button to create new line
    $('.add_on_the_fly_' + ct_id).removeClass('forbidden');

    // Hide empty msg if there is not any line
    if (line_count === 0) {
        $('.empty_msg_' + ct_id).attr('style', 'display:table-row');
    }
};

creme.billing.showEmptyForm = function(btn, ct_id, prefix, line_count) {
    if (btn.hasClass('forbidden')) {
        return;
    }

    btn.addClass('forbidden');

    var form_count_hidden_input = $('#id_' + prefix + '-TOTAL_FORMS');
    var td_inputs = $('.empty_form_inputs_' + ct_id);

    // Replace __prefix__ by form number
    var formCount = parseInt(form_count_hidden_input.val());
    $('input,select,textarea', td_inputs).each(function(index) {
        var input = $(this);
        input.removeClass('bline-input-error');

        var input_id = input.attr('id');
        if (input_id) {
            input.attr('id', input_id.replace('__prefix__', formCount));
        }

        var input_name = input.attr('name');
        if (input_name) {
            input.attr('name', input_name.replace('__prefix__', formCount));
        }
        // Clean empty form with initial model values
        creme.billing.restoreValue(input);
    });

    // Update total forms count
    form_count_hidden_input.val(formCount + 1);

    // Show empty_form
    $('.empty_form_' + ct_id).toggleClass('hidden-form', false);

    // Hide empty msg and empty tr if there is not any line
    if (line_count === 0) {
        $('.space_line_' + ct_id).attr('style', 'display:none');
        $('.empty_msg_' + ct_id).attr('style', 'display:none');
    }
};

creme.billing.restoreValue = function(input) {
    var initial_value = input.attr('initial');

    if (input.attr('type') === 'checkbox') {
        input.prop('checked', !Object.isNone(initial_value));
    } else {
        input.val(initial_value);
    }

    input.trigger('change');
};

creme.billing.restoreInitialValues = function (line_id, form_prefix) {
    creme.dialogs.confirm(gettext('Do you really want to restore initial values of this line?'))
                 .onOk(function() {
                      $('input,select,textarea', $('.restorable_' + line_id)).each(function() {
                          creme.billing.restoreValue($(this));
                      });

                      var delete_checkbox = $('#id_' + form_prefix + '-DELETE');
                      var line_td = $('#line_content_' + line_id);
                      var to_delete = delete_checkbox.prop('checked');

                      if (to_delete) {
                          delete_checkbox.prop('checked', false);
                          line_td.removeClass('bline-deletion-mark');
                          line_td.removeClass('bline-input-error');
                          line_td.addClass('block_header_line_dark');
                      }
                  })
                 .open();
};

// TODO: it would be cool to share this code with Python (the same computing is done on Python side) (pyjamas ??)
creme.billing.initBoundedFields = function (element, currency, global_discount) {
    var discounted = $('[name="discounted"]', element);
    var inclusive_of_tax = $('[name="inclusive_of_tax"]', element);
    var exclusive_of_tax = $('[name="exclusive_of_tax"]', element);
    var container = element.parents('.bline-container:first');

    element.on('change', '.bound', function () {
        // HACK : ignore events from hidden forms (not used onfly or removed onfly)
        if (container.is('.hidden-form')) {
            return;
        }

        var quantity = $('[name*="quantity"]', element);
        var unit_price = $('td input[name*="unit_price"]', element);
        var discount = $('input[name*="discount"]', element);
        var vat_value_widget = $('select[name*="vat_value"]', element);
        var vat_value = $("option[value='" + vat_value_widget.val() + "']", vat_value_widget).text();
        var discount_unit = $('[name*="discount_unit"]', element).val();

        var discounted_value;
        switch (discount_unit) {
            case '1': // DISCOUNT_PERCENT
                discounted_value = quantity.val() * (unit_price.val() - (unit_price.val() * discount.val() / 100));
                break;
            case '2': // DISCOUNT_LINE_AMOUNT
                discounted_value = quantity.val() * unit_price.val() - discount.val();
                break;
            case '3': // DISCOUNT_ITEM_AMOUNT
                discounted_value = quantity.val() * (unit_price.val() - discount.val());
                break;
            default:
                console.log("Bad discount value ?!", discount_unit);
        }

        discounted_value = discounted_value - (discounted_value * global_discount / 100);

        var exclusive_of_tax_discounted = Math.round(discounted_value * 100) / 100;
        var is_discount_invalid = !creme.billing.checkDiscount(discount);

        discount.toggleClass('bline-input-error', is_discount_invalid);

        if (isNaN(exclusive_of_tax_discounted) || is_discount_invalid || !creme.billing.checkPositiveDecimal(quantity)) {
            discounted.text('###');
            inclusive_of_tax.text('###');
            exclusive_of_tax.text('###');
        } else {
            var eot_value = Math.round(quantity.val() * unit_price.val() * 100) / 100;
            var iot_value = Math.round((parseFloat(exclusive_of_tax_discounted) + parseFloat(exclusive_of_tax_discounted) * vat_value / 100) * 100) / 100;

            // TODO: use l10n formatting
            exclusive_of_tax.text(eot_value.toFixed(2).replace(".", ",") + " " + currency);
            discounted.text(exclusive_of_tax_discounted.toFixed(2).replace(".", ",") + " " + currency);
            inclusive_of_tax.text(iot_value.toFixed(2).replace(".", ",") + " " + currency);

            discounted.attr('data-value', exclusive_of_tax_discounted);
            inclusive_of_tax.attr('data-value', iot_value);

            creme.billing.updateBrickTotals(currency);
        }

        if (!vat_value_widget.val()) {
            inclusive_of_tax.text('###');
        }
    });
};

creme.billing.checkModifiedOnUnload = function() {
    if (creme.billing.modifiedBLineForms().first().length) {
        return gettext("You modified your lines.");
    }
};

creme.billing.initLinesBrick = function(brick) {
    var brick_element = brick._element;
    var currency        = brick_element.attr('data-type-currency');
    var global_discount = parseFloat(brick_element.attr('data-type-global-discount'));

    creme.billing.initializeForms(brick_element);

    $('.linetable', brick_element).each(function(index) {
        creme.billing.initBoundedFields($(this), currency, global_discount);
    });

    // TODO: hack because CSS class bound is not added to joe's widget
    $('select[name*="vat_value"]', brick_element).each(function(index) {
        $(this).addClass('bound line-vat');
    });

    setupLineSort(brick);
};

creme.billing.serializeForm = function(form) {
    var data = {};

    creme.billing.inputs($(form)).each(function() {
        var item = creme.billing.serializeInput($(this));

        if (item !== undefined) {
            data[item.key] = item.value;
        }
    });

    return data;
};


creme.billing.updateBrickTotals = function(currency) {
    var total_no_vat_element = $('h1[name=total_no_vat]');
    var total_vat_element    = $('h1[name=total_vat]');

    var total_no_vat = 0;
    var total_vat = 0;

    $('td[name=discounted]').each(function() {
        total_no_vat += parseFloat($(this).attr('data-value'));
    });

    $('td[name=inclusive_of_tax]').each(function() {
        total_vat += parseFloat($(this).attr('data-value'));
    });

    // TODO: use i18n/l10n formatting
    total_no_vat_element.text(total_no_vat.toFixed(2).replace('.', ',') + ' ' + currency);
    total_vat_element.text(total_vat.toFixed(2).replace('.', ',') + ' ' + currency);
};

function setupLineSort(brick) {
    var lines = brick.element().find('.bline-form');

    lines.sortable({
        items:   '.bline-sortable',
        placeholder: 'bline-ghost',
        handle: '.bline-reorder-anchor',
        opacity: 0.8,
        revert:  200,
        delay:   200,
        stop:  function(event, ui) {
            var item = ui.item;
            var next = item.index('.bline-sortable') + 1;
            var prev = parseInt(item.data('bline-order'));
            var url = item.data('bline-reorder-url');

            if (next !== prev) {
                brick.action('update', url, {}, {target: next})
                     .on('fail', function() { brick.refresh(); })
                     .start();
            }
        }
    });
}

}(jQuery));
