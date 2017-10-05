/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2017  Hybird

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

creme.billing.selectDefaultPayment = function(payment_id, invoice_id, reload_url) {
    console.warn('creme.billing.selectDefaultPayment() is deprecated.');

    creme.blocks.ajaxPOSTQuery('/billing/payment_information/set_default/%s/%s'.format(payment_id, invoice_id),
                               {blockReloadUrl: reload_url})
                .start();
};

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
    // 100[.][0-99] ou [0-99][.][0-99]
    return element.val().match(/^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/) !== null;
};

creme.billing.checkValue = function(element) {
//    return element.val() !== '';
    return Boolean(element.val());
};

creme.billing.checkDiscount = function(element) {
    var parent_tr      = element.closest('tr');
    var discount_unit  = parseInt($('select[name*=discount_unit]', parent_tr).val());
    var total_discount = $('input[name*=total_discount]', parent_tr).is(':checked');
    var discount_value = parseFloat($('input[name*=discount]', parent_tr).val());
    var unit_price     = parseFloat($('input[name*=unit_price]', parent_tr).val());
    var quantity       = parseInt($('input[name*=quantity]', parent_tr).val());

    if (!creme.billing.checkPercent(element) && discount_unit == 1) {
        return false;
    }
    if (total_discount && discount_unit == 2 && discount_value > unit_price * quantity) {
        return false;
    }
    if (!total_discount && discount_unit == 2 && discount_value > unit_price) {
        return false;
    }

    return true;
};

// TODO: remove 'ct_id' (useless with the modifications of 9/12/2016)
creme.billing.markDelete = function(form_prefix, ct_id, line_id) {
    var checkbox_name = form_prefix + '-DELETE';
    var delete_checkbox = $('#id_' + checkbox_name);
    var line_td = $('#line_content_' + line_id);

    var to_delete = !delete_checkbox.is(':checked');

    if (!to_delete) {
        delete_checkbox.uncheck();
//        line_td.removeClass('td_error');
        line_td.removeClass('bline-deletion-mark');
        line_td.addClass('block_header_line_dark');
    } else {
        delete_checkbox.check();
//        line_td.addClass('td_error');
        line_td.addClass('bline-deletion-mark');
        line_td.removeClass('block_header_line_dark');
    }

    // TODO: remove the id of <tbody> ??
//    var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
//    tbodyform.toggleClass('form_modified', to_delete);
};

creme.billing.inputs = function(element) {
    return $('input, select, textarea', element);
};

creme.billing.forms = function(element) {
//    return $('tbody[id^="form_id_"]', element);
    return $('.bline-form', element);
};

creme.billing.modifiedBLineForms = function() {
    return $('.bline-form').filter(function() {
        return Boolean(($('> :not(.hidden-form) .bline-input-modified, .bline-deletion-mark', $(this)).first().length));
    })
};

creme.billing.formsHaveErrors = function() {
//    return Boolean($('tbody[id^=form_id_] > :not(.empty_form) .bline-input-error').first().length);
    return Boolean($('.bline-form > :not(.hidden-form) .bline-input-error').first().length);
};

creme.billing.serializeInput = function(input, for_initial) {
    var key = input.attr('name');
    var value = input.attr('type') === 'checkbox' ? (input.is(':checked') ? input.val() : undefined) : input.val();

    // TODO: hack to retrieve creme widget (new attribute will surely be less dirty)
    if (input.attr('o2m') && for_initial) value = input.attr('initial');

    if (key !== undefined && value !== undefined) {
        return {key: key, value: value};
    }

    return;
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
//    input.toggleClass('td_error', !isvalid);
    input.toggleClass('bline-input-error', !isvalid);

    return isvalid;
};

creme.billing.initializeForm = function(element) {
    creme.billing.inputs(element).each(function() {
        var input = $(this);
        var item = creme.billing.serializeInput(input, true);
        input.attr('initial', item !== undefined ? item.value : undefined);
        creme.billing.validateInput(input);
//        element.removeAttr('form_modified');
    });

    // Bind twice because of double init of blocks, seems to not cause a problem
    creme.billing.inputs(element).bind('propertychange input change paste', function() {
        var input = $(this);
        var item = creme.billing.serializeInput(input, false);
        var changed = (item !== undefined && ('' + item.value !== input.attr('initial')));

        if (input.attr('type') === 'checkbox' && item === undefined && input.attr('initial')) {
            changed = true;
        }

//        changed ? creme.billing.validateInput(input) : input.removeClass('td_error');  // bline-input-error
        creme.billing.validateInput(input);

//        input.toggleClass('item_modified', changed);
        input.toggleClass('bline-input-modified', changed);
//        element.toggleClass('form_modified', changed);
    });
};

creme.billing.initializeForms = function(element) {
    creme.billing.forms(element).each(function() {
        creme.billing.initializeForm($(this));
    });
};

creme.billing.hideEmptyForm = function(ct_id, formset_prefix, line_count) {
//    $('.empty_form_' + ct_id).attr('style', 'display:none');
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
    if (btn.hasClass('forbidden')) return;

    btn.addClass('forbidden');

    var form_count_hidden_input = $('#id_' + prefix + '-TOTAL_FORMS');
    var td_inputs = $('.empty_form_inputs_' + ct_id);

    // Replace __prefix__ by form number
    var formCount = parseInt(form_count_hidden_input.val());
    $('input,select,textarea', td_inputs).each(function(index) {
        var input = $(this);
//        input.removeClass('td_error');
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

//    // Set related form as modified
//    var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
//    tbodyform.addClass('form_modified');

    // Show empty_form
//    $('.empty_form_' + ct_id).attr('style', 'display:table-row');
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
        input.get().checked = !Object.isNone(initial_value);
    } else {
        input.val(initial_value);
    }

    input.change();
};

creme.billing.restoreInitialValues = function (line_id, form_prefix, ct_id) {
    creme.dialogs.confirm(gettext('Do you really want to restore initial values of this line ?'))
                 .onOk(function() {
                      $('input,select,textarea', $('.restorable_' + line_id)).each(function(){
                          creme.billing.restoreValue($(this));
                      });

                      var delete_checkbox = $('#id_' + form_prefix + '-DELETE');
                      var line_td = $('#line_content_' + line_id);
                      var to_delete = !delete_checkbox.is(':checked');

                      if (!to_delete) {
                          delete_checkbox.uncheck();
//                          line_td.removeClass('td_error');
                          line_td.removeClass('bline-input-error');
                          line_td.addClass('block_header_line_dark');
                      }

//                      var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
//                      tbodyform.toggleClass('form_modified', to_delete);
                  })
                 .open();
};

//TODO: it would be cool to share this code with Python (the same computing is done on Python side) (pyjamas ??)
creme.billing.initBoundedFields = function (element, currency, global_discount) {
    var discounted = $('[name="discounted"]', element);
    var inclusive_of_tax = $('[name="inclusive_of_tax"]', element);
    var exclusive_of_tax = $('[name="exclusive_of_tax"]', element);

    element.delegate('.bound', 'change', function () {
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

//        discount.toggleClass('td_error', is_discount_invalid);
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

            creme.billing.updateBlockTotals(currency);
        }

        if (!vat_value_widget.val()) inclusive_of_tax.text('###');
    });
};

creme.billing.checkModifiedOnUnload = function() {
//    if ($('.item_modified').length != 0 || $('.form_modified').length != 0) {
    if (creme.billing.modifiedBLineForms().first().length) {
        return gettext("You modified your lines.")
    }
};

creme.billing.reload = function(checkmodified) {
    console.warn('creme.billing.reload() is deprecated.');
    creme.billing.redirect('', checkmodified);
};

creme.billing.redirect = function(url, checkmodified) {
    console.warn('creme.billing.redirect() is deprecated.');

    var checkmodified = checkmodified === undefined ? true : checkmodified;

    if (!checkmodified) {
        $(window).unbind('beforeunload', creme.billing.checkModifiedOnUnload);
    }

    window.location = url;
};

//creme.billing.initBlockLines = function(currency, global_discount) {
creme.billing.initLinesBrick = function(brick) {
    var brick_element = brick._element;
    var currency        = brick_element.attr('data-type-currency');
    var global_discount = parseFloat(brick_element.attr('data-type-global-discount'));

//    creme.billing.initializeForms();
    creme.billing.initializeForms(brick_element);

    // Commented on 03/04/2016, because it seemed useless
//    $('a[class^="add_on_the_fly_"]').removeAttr('disabled');

//    $('.linetable').each(function(index) {
    $('.linetable', brick_element).each(function(index) {
        creme.billing.initBoundedFields($(this), currency, global_discount);
    });

    // TODO: hack because CSS class bound is not added to joe's widget
//    $('select[name*="vat_value"]').each(function(index) {
    $('select[name*="vat_value"]', brick_element).each(function(index) {
        $(this).addClass('bound line-vat');
    });

//    $('textarea.line-comment').each(function() {
    $('textarea.line-comment', brick_element).each(function() {
        new creme.layout.TextAreaAutoSize().bind($(this));
    });
};

creme.billing.serializeForm = function(form) {
    var data = {};

    creme.billing.inputs($(form)).each(function() {
        var item = creme.billing.serializeInput($(this), false);

        if (item !== undefined) {
            data[item.key] = item.value;
        }
    });

    return data;
};

//creme.billing.multiSaveLines = function(document_id) {
creme.billing.multiSaveLines = function(save_url) {
    console.warn('creme.billing.multiSaveLines() is deprecated ; use the new brick action "billing-line-saveall" instead.');

    if (creme.billing.formsHaveErrors()) {
        creme.dialogs.alert('<p>' + gettext('There are some errors in your lines.') + '</p>').open();
    } else {
        var forms_data = {};
        var blocks_reload_url = '';
        var blocks_deps = '';

        // TODO: do not ask confirmation to leave the page in this precise case
//        var blocks_to_reload = $('tbody[id^=form_id_]').filter('.form_modified').map(function() {
//            var container = $(this);
//            var ct_id = container.attr('ct_id');
//            forms_data[ct_id] = $.toJSON(creme.billing.serializeForm(container));
//
//            return container.attr('reload_url') + creme.utils.getBlocksDeps(container.attr('block_name'));
//        }).get();
        creme.billing.modifiedBLineForms().each(function() {
            var container = $(this);
            forms_data[container.attr('ct_id')] = $.toJSON(creme.billing.serializeForm(container));
            blocks_reload_url = blocks_reload_url || container.attr('reload_url');

            var block_name = container.attr('block_name');
            if (!blocks_deps) {
                blocks_deps = creme.utils.getBlocksDeps(block_name);
            } else {
                if (!blocks_deps.match(block_name)) {
                    // NB: the line blocks should be inter-dependant, so this code should be useless
                    blocks_deps += ',' + block_name;
                }
            }
        }).get();

        if (!blocks_reload_url) {
            console.log('Forms not modified !');
            return;
        }

//        creme.utils.ajaxQuery('/billing/%s/multi_save_lines'.format(document_id),
        creme.utils.ajaxQuery(save_url,
                              {action: 'post', warnOnFail: true, warnOnFailTitle: gettext('Errors report')},
                              forms_data)
                   .onDone(function() {
//                        blocks_to_reload.forEach(function(block_url) {
//                            creme.blocks.reload(block_url);
//                        });
                        creme.blocks.reload(blocks_reload_url + blocks_deps);
                    })
                   .start();
    }
};

creme.billing.updateBlockTotals = function(currency) {
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

creme.billing.EXPORT_FORMATS = [
   //{value:'odt', label: gettext("Document open-office (ODT)")},
   {value: 'pdf', label: gettext("Pdf file (PDF)")}
];

creme.billing.exportAs = function(url, formats) {
    var formats = formats || creme.billing.EXPORT_FORMATS;

    if (formats.length === 1) {
        window.location.href = url.format(formats[0].value);
        return;
    }

    creme.dialogs.choice(gettext("Select the export format of your billing document"), {choices: formats})
                 .onOk(function(event, data) {
                     window.location.href = url.format(data);
                 }).open();
};

creme.billing.convertAs = function(billing_id, type) {
    console.warn('creme.billing.convertAs() is deprecated.');

    // XXX: pass the reversed URL as argument (instead of 'billing_id') if you want a correct version of this function
    return creme.utils.ajaxQuery('/billing/%s/convert/'.format(billing_id),
                                 {action: 'post', warnOnFail: true, reloadOnSuccess: true},
                                 {type:type})
                      .start();
};

creme.billing.generateInvoiceNumber = function(url) {
    return creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true, reloadOnSuccess: true})
                      .start();
};

//creme.billing.linkToDocument = function(url, organisations) {
//    console.warn('This function is deprecated.');
//    if (Object.isEmpty(organisations))
//        return;
//
//    if (organisations.length === 1) {
//        creme.dialogs.form(url + organisations[0].value, {reloadOnSuccess: true}).open({width:'80%'});
//        return;
//    }
//
//    creme.dialogs.choice(gettext('Who is the source, managed by Creme, for your billing document ?'),
//                         {choices:organisations, title: gettext('Billing')})
//                 .onOk(function(event, orga_id) {
//                     creme.dialogs.form(url + orga_id, {reloadOnSuccess: true}).open({width:'80%'});
//                  })
//                 .open();
//};

(function() {
    var billingLinesActions = {
        _action_billing_line_addonfly: function(url, options, data, e) {
            return new creme.component.Action(function() {
                var count = data.count ? parseInt(data.count) : 0;
                creme.billing.showEmptyForm($(e.currentTarget), data.ctype_id, data.prefix, count);
                this.done();
            });
        },

        _action_billing_line_saveall: function(url, options, data, e) {
            var brick = this;

            return new creme.component.Action(function() {
                if (creme.billing.formsHaveErrors()) {
                    creme.dialogs.alert('<p>' + gettext('There are some errors in your lines.') + '</p>').open();
                } else {
                    var forms_data = {};

                    creme.billing.modifiedBLineForms().each(function() {
                        var container = $(this);
                        forms_data[container.attr('ct_id')] = $.toJSON(creme.billing.serializeForm(container));
                    });

                    if (forms_data.length === 0) {
                        console.log('Forms not modified !');
                        return this.cancel();
                    }

                    creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true, warnOnFailTitle: gettext('Errors report')}, forms_data)
                               .onDone(function() {brick.refresh();})
                               .onFail(this.fail.bind(this))
                               .start();
                }
            });
        },

        _action_billing_line_clearonfly: function(url, action, data, e) {
            var brick = this;

            return new creme.component.Action(function() {
                creme.billing.hideEmptyForm(data.ctype_id, data.prefix, data.count);
                $('[data-action="billing-line-addonfly"]', brick._element).removeClass('forbidden');
                this.done();
            });
        }
    };

    $(document).on('brick-before-bind', '.brick.billing-lines-brick', function(e, brick, options) {$.extend(brick, billingLinesActions);})
               .on('brick-ready', function(e, brick, options) {creme.billing.initLinesBrick(brick);});
}());

}(jQuery));
