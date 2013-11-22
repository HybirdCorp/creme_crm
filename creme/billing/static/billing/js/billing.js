/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.billing = creme.billing || {};

// Commented 1/7/2013 (view has been commented too)
// creme.billing.lineAutoPopulateSelection = function(id, targetInputId, nodesToPopulate) {
//     var $form = $('#' + targetInputId).parents('form');
//     var fields = nodesToPopulate.values;
//
//     creme.ajax.json.post(
//         '/creme_core/entity/json',
//         {
//             pk:     id[0],
//             fields: fields
//         },
//         function(data) {
//             for(var i in fields) {
//                 var field = nodesToPopulate.values[i];
//                 var node = $form.find('[' + nodesToPopulate.attr + '=' + field + ']');
//                 if(node.size() > 0) {
//                     node.val(data[0].fields[field]);
//                 }
//             }
//         }
//     );
// }

//creme.billing.enableCheckAllBoxes = function(checkbox) {
//    var table = checkbox.parents("tbody:first");
//
//    if(checkbox.is(':checked')) {
//        $('td input[name="select_one"]', table).check();
//    } else {
//        $('td input[name="select_one"]', table).uncheck();
//    }
//}

//creme.billing.get_selected_lines = function() { //TODO: rename (camelCase)
//    var selected_lines_ids = new Array();
//    var lines = $('[name="select_one"]');
//
//    lines.each(function () {
//        var currentLine = $(this);
//        if(currentLine.is(':checked'))
//            selected_lines_ids.push(currentLine.val());
//    })
//    return selected_lines_ids;
//}

//creme.billing.multipleLineDelete = function(reload_url) {
//    var selected_lines_ids = creme.billing.get_selected_lines();
//
//    if(selected_lines_ids.length == 0){
//        creme.utils.showDialog(gettext("Nothing is selected."));
//        return;
//    }
//
//    var ajax_opts = {
//        'complete': function(data, status) {
//                creme.utils.loadBlock(reload_url);
//        }
//    };
//
//    creme.utils.ajaxDelete('/creme_core/entity/delete/multi', {'ids' : selected_lines_ids.toString()}, ajax_opts, gettext("Are you sure ?"));
//}

//creme.billing.bulkLineUpdate = function(reload_url, ct_id) {
//    var selected_lines_ids = creme.billing.get_selected_lines();
//
//    if(selected_lines_ids.length == 0){
//        creme.utils.showDialog(gettext("Nothing is selected."));
//        return;
//    }
//
//    var ajax_opts = {
//        'data' : {'persist' : new Array('ids'), 'ids' : selected_lines_ids}
//    };
//
//    var options = {'beforeClose' : function() {creme.utils.loadBlock(reload_url);}}
//
//    creme.utils.showInnerPopup('/creme_core/entity/bulk_update/' + ct_id + '/', options, undefined, ajax_opts);
//}

//creme.billing.checkPositiveDecimal = function(value) {
//    return value.match(/^[0-9]+(\.[0-9]{1,2}){0,1}$/) ? null : "This is not a positive decimal number !";
//}
//
//creme.billing.checkPositiveInteger = function(value) {
//    return value.match(/^[0-9]+$/) ? null : "This is not a positive integer !";
//}
//
//creme.billing.checkDecimal = function(value) {
//    return value.match(/^[\-]{0,1}[0-9]+(\.[0-9]{1,2}){0,1}$/) ? null : "This is not a decimal number !";
//}
//
//creme.billing.checkPercent = function(value) {
//    // 100[.][0-99] ou [0-99][.][0-99]
//    // /^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/
//    return value.match(/^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/) ? null : "This is not a percentage !";
//}
//
//creme.billing.checkValue = function(value) {
//    return value ? null : gettext("A value is needed for this field !");
//}

//creme.billing.printLinesErrors = function(target, table, reload_url) {
//    target.addClass('line-error');
//    var message_one = gettext("Some errors were found on your lines. Click => ");
//    var message_two = gettext("here");
//    var message_three = "<a onclick='creme.utils.loadBlock(\"" + reload_url + "\");'><b>" + message_two + "</b></a> ";
//    var message_four = gettext("<= to restore the last coherent state. An error correction will restabilize all other ones.");
//    target.html(message_one + message_three + message_four);
//
//    var ul = $('<ul/>');
//
//    $("td.discount-functional-error", table).each(function() {
//        ul.append($('<li/>').html("<font color=red><b>" + $(this).attr("discount-functional-errormessage") + "</b></font>"));
//    });
//
//    target.append(ul);
//}

//creme.billing.validateDiscount = function(line) {
//    var discount_unit   = parseInt($('select[name=discount_unit]', line).val());
//    var discount_total  = parseInt($('select[name=total_discount]', line).val());
//    var discount_value  = parseFloat($('input[name=discount]', line).val());
//    var unit_price      = parseFloat($('input[name=unit_price]',line).val());
//    var quantity        = parseInt($('input[name=quantity]', line).val());
//
//    if (creme.billing.checkPercent($('input[name=discount]', line).val()) !== null && discount_unit == 1) {
//        return gettext("Invalid percentage.");
//    }
//    if (discount_total == 1 && discount_unit == 2 && discount_value > unit_price * quantity) {
//        return gettext("Your discount amount is superior than the amount of the line where you try to apply it.");
//    }
//    if (discount_total == 2 && discount_unit == 2 && discount_value > unit_price) {
//        return gettext("Your unit discount is superior than the unit price of the product/service of the line where you try to apply it.");
//    }
//
//    return null;
//}

//creme.billing.validateDiscountForm = function(line, reload_url) {
//    var tbody = line.parents('tbody:first');
//    var table_errors = $('td#error_lines', line.parents('table:first'));
//
//    var form_error = creme.billing.validateDiscount(line);
//
//    if (form_error != null) {
//        var line_error_message_first = gettext("On the line");
//        var error_message = line_error_message_first + " <" + $('input#line_number', line).val() + "> : " + form_error;
//        $('td#discount_td', line).addClass('discount-functional-error')
//                                 .attr('discount-functional-errormessage', error_message);
//
//        creme.billing.printLinesErrors(table_errors, tbody, reload_url);
//        return false;
//    }
//
//    table_errors.removeClass('line-error');
//    $('td#discount_td', line).removeClass('discount-functional-error')
//                             .removeAttr('discount-functional-errormessage');
//
//    return true;
//}

//creme.billing.mapInputs = function (form) {
//    var data = {};
//
//    $('input:enabled, select:enabled', form).each(function()
//    {
//        var key = $(this).attr('name');
//        var value = $(this).val()
//        if (key !== undefined && value !== undefined)
//            data[key] = value;
//    });
//    return data;
//}

//creme.billing.submitLine = function(input, reload_url, validator) {
//    var line = input.parents('tr.content:first');
//
//    if (validator != null) {
//        var error = validator(input.val());
//    } else {
//        var error = null;
//    }
//
//    var isDiscountFormValid = creme.billing.validateDiscountForm(line, reload_url);
//
//    if(error === null) {
//        if(isDiscountFormValid) {
//            var defaults = {
//                'success': function(data, status) {
//                    creme.utils.loadBlock(reload_url);
//                }
//            }
//            var datas = creme.billing.mapInputs(line);
//            creme.ajax.submit(line, creme.billing.mapInputs(line), defaults);
//            $(input).removeClass('creme-field-error');
//            $(input).removeAttr('creme-field-errormessage');
//        }
//    } else {
//        $(input).addClass('creme-field-error');
//        $(input).attr('creme-field-errormessage', gettext(error));
//    }
//}

creme.billing.selectDefaultPayment = function(payment_id, invoice_id, reload_url) {
    creme.blocks.ajaxPOSTQuery('/billing/payment_information/set_default/%s/%s'.format(payment_id, invoice_id),
                               {blockReloadUrl: reload_url})
                .start();
}

// TODO move most of these functions in core

creme.billing.checkPositiveDecimal = function(element) {
    return element.val().match(/^[0-9]+(\.[0-9]{1,2}){0,1}$/) !== null;
}

creme.billing.checkPositiveInteger = function(element) {
    return element.val().match(/^[0-9]+$/) !== null;
}

creme.billing.checkDecimal = function(element) {
    return element.val().match(/^[\-]{0,1}[0-9]+(\.[0-9]{1,2}){0,1}$/) !== null;
}

creme.billing.checkPercent = function(element) {
    // 100[.][0-99] ou [0-99][.][0-99]
    // /^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/
    return element.val().match(/^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/) !== null;
}

creme.billing.checkValue = function(element) {
    return element.val() !== '';
}

creme.billing.checkDiscount = function(element) {
    var parent_tr       = element.closest('tr');
    var discount_unit   = parseInt($('select[name*=discount_unit]', parent_tr).val());
    var total_discount  = $('input[name*=total_discount]', parent_tr).is(':checked');
    var discount_value  = parseFloat($('input[name*=discount]',parent_tr).val());
    var unit_price      = parseFloat($('input[name*=unit_price]',parent_tr).val());
    var quantity        = parseInt($('input[name*=quantity]', parent_tr).val());

//    console.log('prix unitaire : ' + unit_price + ", quantité : " + quantity + ", remise globale ? " + total_discount + ", remise : " + discount_value + ", discount unit : " + discount_unit);

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
}

creme.billing.markDelete = function(form_prefix, ct_id, line_id) {
    var checkbox_name = form_prefix + '-DELETE';
    var delete_checkbox = $('#id_' + checkbox_name);
    var line_td = $('#line_content_' + line_id);

    var to_delete = !delete_checkbox.is(':checked');

    if (!to_delete) {
        delete_checkbox.uncheck();
        line_td.removeClass('td_error');
        line_td.addClass('block_header_line_dark');
    } else {
        delete_checkbox.check();
        line_td.addClass('td_error');
        line_td.removeClass('block_header_line_dark');
    }

    var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
    tbodyform.toggleClass('form_modified', to_delete);
}

creme.billing.inputs = function(element) {
    return $('input, select, textarea', element);
}

creme.billing.forms = function(element) {
    return $('tbody[id^="form_id_"]', element);
}

creme.billing.serializeInput = function(input, for_initial) {
    var key = input.attr('name');
    var value = input.attr('type') === 'checkbox' ? (input.is(':checked') ? input.val() : undefined) : input.val();

    // TODO hack to retrieve creme widget (new attribute will surely be les dirty)
    if (input.attr('o2m') && for_initial) value = input.attr('initial');

    if (key !== undefined && value !== undefined) {
        return {key: key, value: value};
    }

    return;
}

creme.billing.validateInput = function(input) {
    var validator = input.attr('validator') ? creme.billing['check' + input.attr('validator')] : undefined;
    var isvalid = input.attr('isvalid') || false;

    if (typeof validator === 'function') {
        isvalid = validator(input);
    } else {
        isvalid = true;
    }

    input.attr('isvalid', isvalid);

    isvalid ? input.removeClass('td_error') : input.addClass('td_error');

    return isvalid;
}

creme.billing.initializeForm = function(element) {
    creme.billing.inputs(element).each(function() {
        var item = creme.billing.serializeInput($(this), true);
        $(this).attr('initial', item !== undefined ? item.value : undefined);
        creme.billing.validateInput($(this));
        element.removeAttr('form_modified');
    });

    // bind twice because of double init of blocks, seems to not coz no problem
    creme.billing.inputs(element).bind('change', function() {
        var item = creme.billing.serializeInput($(this), false);
        var changed = item !== undefined && ('' + item.value !== $(this).attr('initial'));

        if ($(this).attr('type') === 'checkbox' && item === undefined && $(this).attr('initial')) {
            changed = true;
        }

        changed ? creme.billing.validateInput($(this)) : $(this).removeClass('td_error');

        $(this).toggleClass('item_modified', changed);
        element.toggleClass('form_modified', changed);
    });
}

creme.billing.initializeForms = function(element) {
    creme.billing.forms(element).each(function() {
        creme.billing.initializeForm($(this));
    });
}

creme.billing.hideEmptyForm = function(ct_id, formset_prefix, line_count) {
    $('.empty_form_' + ct_id).attr('style', 'display:none');
    // update total forms count
    var form_count_hidden_input = $('#id_' + formset_prefix + '-TOTAL_FORMS');
    form_count_hidden_input.val(parseInt(form_count_hidden_input.val()) - 1);
    // console.log('TOTAL FORMS = ' + form_count_hidden_input.val());
    $('.add_on_the_fly_' + ct_id).removeClass('forbidden');

    // hide empty msg if there is not any line
    if (line_count === 0) {
        $('.empty_msg_' + ct_id).attr('style', 'display:table-row');
    }
}

creme.billing.showEmptyForm = function(btn, ct_id, prefix, line_count) {
    if (btn.hasClass('forbidden')) return;

    btn.addClass('forbidden');

    var form_count_hidden_input = $('#id_' + prefix + '-TOTAL_FORMS');
    var td_inputs = $('.empty_form_inputs_' + ct_id);

    // replace __prefix__ by form number
    var formCount = parseInt(form_count_hidden_input.val());
    $('input,select,textarea', td_inputs).each(function(index) {
        $(this).removeClass('td_error');

        if ($(this).attr('id')) {
            $(this).attr('id', $(this).attr('id').replace('__prefix__', formCount));
        }

        if ($(this).attr('name')) {
            $(this).attr('name', $(this).attr('name').replace('__prefix__', formCount));
        }
        // clean empty form with initial model values
        creme.billing.restoreValue($(this));
    });

    // update total forms count
    form_count_hidden_input.val(formCount + 1);

    // set related form as modified
    var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
    tbodyform.addClass('form_modified');

    // show empty_form
    $('.empty_form_' + ct_id).attr('style', 'display:table-row');

    // hide empty msg and empty tr if there is not any line
    if (line_count === 0) {
        $('.space_line_' + ct_id).attr('style', 'display:none');
        $('.empty_msg_' + ct_id).attr('style', 'display:none');
    }
}

// TODO a utiliser si on veut essayer de faire une remontée inline des form error
//creme.billing.submitBlock = function(block, url) {
//    creme.ajax.post({
//                'url': url,
//                'success': function(data, status) {
//                      creme.blocks.fill(block, data);
//                }
//    });
//}

creme.billing.restoreValue = function(input) {
    var initial_value = input.attr('initial');

    if (initial_value !== undefined) {
        if (input.attr('type') === 'checkbox') {
            input.check();
        } else {
            if (input.attr('o2m')) { // TODO hack pour récup le creme entity widget
                if (initial_value === '') {
                    input.val('');
                    $('div', $('div', input.parent())).empty().remove();
                } else {
                    creme.lv_widget.handleSelection(initial_value, input.attr('id'));
                }
            } else {
                    input.val(initial_value);
            }
        }
    } else {
        if (input.attr('type') === 'checkbox') input.uncheck();
    }

    input.change();
}

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
                          line_td.removeClass('td_error');
                          line_td.addClass('block_header_line_dark');
                      }

                      var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
                      tbodyform.toggleClass('form_modified', to_delete);
                  })
                 .open();
}

//creme.billing.restoreInitialValues = function (line_id, form_prefix, ct_id) {
//    var buttons = {};
//
//    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}
//    buttons[gettext("Yes")] = function() {
//        $('input,select,textarea', $('.restorable_' + line_id)).each(function(){
//            creme.billing.restoreValue($(this));
//        });
//
//        var checkbox_name = form_prefix + '-DELETE';
//        var delete_checkbox = $('#id_' + checkbox_name);
//        var line_td = $('#line_content_' + line_id);
//
//        var to_delete = !delete_checkbox.is(':checked');
//
//        if (!to_delete) {
//            delete_checkbox.uncheck();
//            line_td.removeClass('td_error');
//            line_td.addClass('block_header_line_dark');
//        }
//
//        var tbodyform = $('tbody[id^="form_id_' + ct_id + '"]');
//        tbodyform.toggleClass('form_modified', to_delete);
//
//        $(this).dialog("destroy");
//        $(this).remove();
//    }
//
//    creme.utils.showDialog(gettext("Do you really want to restore initial values of this line ?"), {buttons: buttons, title: gettext("Confirmation")});
//}

creme.billing.initBoundedFields = function (element, currency) {
    var discounted = $('[name="discounted"]', element);
    var inclusive_of_tax = $('[name="inclusive_of_tax"]', element);
    var exclusive_of_tax = $('[name="exclusive_of_tax"]', element);

    element.delegate('.bound', 'change', function () {
        var quantity = $('[name*="quantity"]', element);
        var unit_price = $('td input[name*="unit_price"]', element);
        var discount = $('input[name*="discount"]', element);
        var vat_value_widget = $('select[name*="vat_value"]', element);
        var vat_value = $("option[value='"+ vat_value_widget.val() +"']", vat_value_widget).text();
        var discount_unit = $('[name*="discount_unit"]', element);
        var total_discount = $('[name*="total_discount"]', element);

        if(discount_unit.val() == 1) { // percent
            if(total_discount.is(':checked')) {
                var discounted_value = ((quantity.val()*unit_price.val()) - ((quantity.val()*unit_price.val()*discount.val())/100));
            } else {
                var discounted_value = quantity.val()*(unit_price.val()-(unit_price.val()*discount.val()/100));
            }
        } else {
            if(total_discount.is(':checked')) {
                var discounted_value = quantity.val()*unit_price.val()-discount.val();
            } else {
                var discounted_value = quantity.val()*(unit_price.val()-discount.val());
            }
        }

        var global_discount_value = $('[name="overall_discount_document"]').attr('value');

        if (global_discount_value != "") {
            discounted_value = discounted_value-(discounted_value*parseInt(global_discount_value)/100);
        }

        var exclusive_of_tax_discounted = Math.ceil(discounted_value * 100) / 100;

        var is_discount_valid = creme.billing.checkDiscount(discount);

        var discount_closest_td = discount.closest('td');
        is_discount_valid ? discount_closest_td.removeClass('td_error') : discount_closest_td.addClass('td_error');

        if (isNaN(exclusive_of_tax_discounted) || !is_discount_valid || !creme.billing.checkPositiveDecimal(quantity)) {
            discounted.text('###');
            inclusive_of_tax.text('###');
            exclusive_of_tax.text('###');
        } else {
            var ht_value = Math.ceil(quantity.val() * unit_price.val() * 100) / 100;
            var ttc_value = Math.ceil((parseFloat(exclusive_of_tax_discounted)+parseFloat(exclusive_of_tax_discounted)*vat_value/100) * 100) / 100;

            exclusive_of_tax.text(ht_value.toFixed(2).replace(".",",") + " " + currency);
            discounted.text(exclusive_of_tax_discounted.toFixed(2).replace(".",",") + " " + currency);
            inclusive_of_tax.text(ttc_value.toFixed(2).replace(".",",") + " " + currency);

            discounted.attr('value', exclusive_of_tax_discounted);
            inclusive_of_tax.attr('value', ttc_value);

            creme.billing.updateBlockTotals(currency);
        }

        if (!vat_value_widget.val()) inclusive_of_tax.text('###');
    });
}

creme.billing.checkModifiedOnUnload = function() {
    if ($('.item_modified').length != 0 || $('.form_modified').length != 0) {
        return gettext("You modified your lines.")
    }
}

creme.billing.reload = function(checkmodified) {
    creme.billing.redirect('', checkmodified);
}

creme.billing.redirect = function(url, checkmodified) {
    var checkmodified = checkmodified === undefined ? true : checkmodified;

    if (!checkmodified) {
        $(window).unbind('beforeunload', creme.billing.checkModifiedOnUnload);
    }

    window.location = url;
}

creme.billing.initBlockLines = function (currency) {
    creme.billing.initializeForms();

    $('a[class^="add_on_the_fly_"]').removeAttr('disabled');

    $('.linetable').each(function(index) {
        creme.billing.initBoundedFields($(this), currency);
    });

    // TODO hack because css class bound is not added to joe's widget
    $('select[name*="vat_value"]').each(function(index) {
        $(this).addClass('bound line-vat');
    });
}

creme.billing.serializeForm = function(form) {
    var data = {};

    creme.billing.inputs($(form)).each(function() {
        var item = creme.billing.serializeInput($(this), false);

        if (item !== undefined) {
            data[item.key] = item.value;
        }
    });

    return data;
}

creme.billing.multi_save_lines = function (document_id) {
    creme.dialogs.confirm(gettext("Do you really want to save all the modifications done on the lines of this document ?"))
                 .onOk(function() {
                     var forms = $('tbody[id^=form_id_]');
                     var forms_data = {};
                     var url = '/billing/%s/multi_save_lines'.format(document_id);

                     // TODO do not ask confirmation to leave the page in this precise case
                     var blocks_to_reload = forms.filter('.form_modified').map(function() {
                         var ct_id = $(this).attr('ct_id');
                         forms_data[ct_id] = $.toJSON(creme.billing.serializeForm($(this)));
                         return $(this).attr('reload_url') + creme.utils.getBlocksDeps($(this).attr('block_name'));
                     }).get();

                     creme.utils.ajaxQuery(url, {action: 'post'}, forms_data)
                                .onFail(function(event, error, status) {
                                     if (status.status === 409) {
                                         creme.dialogs.warning(unescape(error), {title: gettext('Errors report')}).open();
                                     }
                                 })
                                .onDone(function() {
                                     blocks_to_reload.forEach(function(block_url) {
                                         creme.blocks.reload(block_url);
                                     });
                                 })
                                .start();
                 }).open();
/*
    var buttons = {};

    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}
    buttons[gettext("Yes")] = function() {
        $(this).dialog("destroy");
        $(this).remove();

        var forms = $('tbody[id^=form_id_]');
        var data = {};
        var blocks_reload = new Array();
        var i = 0;

        // TODO do not ask confirmation to leave the page in this precise case
        forms.each(function() {
            if ($(this).hasClass('form_modified')) {
                var ct_id = $(this).attr('ct_id');

                var form_datas = {};
                creme.billing.inputs($(this)).each(function() {
                    var item = creme.billing.serializeInput($(this), false);

                    if (item !== undefined) {
                        form_datas[item.key] = item.value;
                    }
                });

                data[ct_id] = $.toJSON(form_datas);

                blocks_reload[i] = $(this).attr('reload_url') + creme.utils.getBlocksDeps($(this).attr('block_name'));
                i = i + 1;
            }
        });

        $.ajax({
            type: "POST",
            url: '/billing/' + document_id + '/multi_save_lines',
            data : data,
            dataType : "json",
            error : function(request, textStatus, errorThrown){
                if(request.status == 409){
                    creme.utils.loading('loading', true, {});
                    creme.utils.showDialog(unescape(request.responseText), {'title': gettext("Errors report")});
                }
            },
            beforeSend: function(request) {
                creme.utils.loading('loading', false, {});
            },
            success : function(request, txtStatus) {
                if (blocks_reload.length != 0) {
                    for(var i = 0; i < blocks_reload.length; i++) {
                        creme.utils.loadBlock(blocks_reload[i]);
                    }
                } else {
                    creme.utils.loading('loading', true, {});
                }
            }
        });
    }

    creme.utils.showDialog(gettext("Do you really want to save all the modifications done on the lines of this document ?"), {buttons: buttons, title:gettext("Confirmation")});
*/
}

creme.billing.updateBlockTotals = function(currency) {
    var total_no_vat_element = $('h1[name=total_no_vat]');
    var total_vat_element    = $('h1[name=total_vat]');

    var total_no_vat = 0;
    var total_vat = 0;

    $('td[name=discounted]').each(function() {
        total_no_vat += parseFloat($(this).attr('value'));
    });

    $('td[name=inclusive_of_tax]').each(function() {
        total_vat += parseFloat($(this).attr('value'));
    });

    total_no_vat_element.text(total_no_vat.toFixed(2).replace(".",",") + " " + currency);
    total_vat_element.text(total_vat.toFixed(2).replace(".",",") + " " + currency);
}

creme.billing.EXPORT_FORMATS = [
   //{value:'odt', label: gettext("Document open-office (ODT)")},
   {value:'pdf', label: gettext("Pdf file (PDF)")}
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
}

creme.billing.convertAs = function (billing_id, type) {
    return creme.utils.ajaxQuery('/billing/%s/convert/'.format(billing_id),
                                 {action: 'post', warnOnFail: true, reloadOnSuccess: true},
                                 {type:type})
                      .start();
}

creme.billing.generateInvoiceNumber = function(billing_id) {
    return creme.utils.ajaxQuery('/billing/invoice/generate_number/%s'.format(billing_id),
                                 {action: 'post', warnOnFail: true, reloadOnSuccess: true})
                      .start();
}

creme.billing.linkToDocument = function(url, organisations) {
    if (Object.isEmpty(organisations))
        return;

    creme.dialogs.choice(gettext('Who is the source, managed by Creme, for your billing document ?'),
                         {choices:organisations, title: gettext('Billing')})
                 .onOk(function(event, orga_id) {
                     creme.dialogs.deprecatedForm(url + orga_id, {reloadOnSuccess:true}).open({width:'80%'});
                  })
                 .open();
}
