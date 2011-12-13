/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.billing = {};

creme.billing.lineAutoPopulateSelection = function(id, targetInputId, nodesToPopulate) {
    var $form = $('#' + targetInputId).parents('form');
    var fields = nodesToPopulate.values;

    creme.ajax.json.post(
        '/creme_core/entity/json',
        {
            pk:     id[0],
            fields: fields
        },
        function(data) {
            for(var i in fields) {
                var field = nodesToPopulate.values[i];
                var node = $form.find('[' + nodesToPopulate.attr + '=' + field + ']');
                if(node.size() > 0) {
                    node.val(data[0].fields[field]);
                }
            }
        }
    );
}

creme.billing.setDefaultPaymentInformation = function(payment_info_id, invoice_id, reload_url) {
    creme.utils.postNReload('/billing/payment_information/set_default/'+payment_info_id+'/'+invoice_id, reload_url);
}

creme.billing.enableCheckAllBoxes = function(checkbox) {
    var table = checkbox.parents("tbody:first");

    if(checkbox.is(':checked')) {
        $('td input[name="select_one"]', table).check();
    } else {
        $('td input[name="select_one"]', table).uncheck();
    }
}

creme.billing.get_selected_lines = function() {
    var selected_lines_ids = new Array();
    var lines = $('[name="select_one"]');

    lines.each(function () {
        var currentLine = $(this);
        if(currentLine.is(':checked'))
            selected_lines_ids.push(currentLine.val());
    })
    return selected_lines_ids;
}

creme.billing.multipleLineDelete = function(reload_url) {
    var selected_lines_ids = creme.billing.get_selected_lines();

    if(selected_lines_ids.length == 0){
        creme.utils.showDialog(gettext("Nothing is selected."));
        return;
    }

    var ajax_opts = {
        'complete': function(data, status) {
                creme.utils.loadBlock(reload_url);
        }
    };

    creme.utils.ajaxDelete('/creme_core/delete_js', {'ids' : selected_lines_ids.toString()}, ajax_opts, gettext("Are you sure ?"));
}

creme.billing.bulkLineUpdate = function(reload_url, ct_id) {
    var selected_lines_ids = creme.billing.get_selected_lines();

    if(selected_lines_ids.length == 0){
        creme.utils.showDialog(gettext("Nothing is selected."));
        return;
    }

    var ajax_opts = {
        'data' : {'persist' : new Array('ids'), 'ids' : selected_lines_ids}
    };

    var options = {'beforeClose' : function() {creme.utils.loadBlock(reload_url);}}

    creme.utils.showInnerPopup('/creme_core/entity/bulk_update/' + ct_id + '/', options, undefined, ajax_opts);
}

creme.billing.checkPositiveDecimal = function(value) {
    return value.match(/^[0-9]+(\.[0-9]{1,2}){0,1}$/) ? null : "This is not a positive decimal number !";
}

creme.billing.checkPositiveInteger = function(value) {
    return value.match(/^[0-9]+$/) ? null : "This is not a positive integer !";
}

creme.billing.checkDecimal = function(value) {
    return value.match(/^[\-]{0,1}[0-9]+(\.[0-9]{1,2}){0,1}$/) ? null : "This is not a decimal number !";
}

creme.billing.checkPercent = function(value) {
    // 100[.][0-99] ou [0-99][.][0-99]
    // /^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/
    return value.match(/^(100(\.[0]{1,2}){0,1}|[0-9]{1,2}(\.[0-9]{1,2}){0,1})$/) ? null : "This is not a percentage !";
}

creme.billing.printLinesErrors = function(target, table, reload_url) {

    target.addClass('line-error');
    // TODO gettext
    target.html("Des erreurs ont été trouvées sur vos lignes. Cliquez => <a onclick='creme.utils.loadBlock(\"" + reload_url + "\");'><b>ici</b></a> <= pour retrouver le dernier état cohérent. La correction d'une erreur sur une ligne restabilisera toutes les autres lignes.");

    var ul = $('<ul/>');

    $("td.discount-functional-error", table).each(function() {
        ul.append($('<li/>').html("<font color=red><b>" + $(this).attr("discount-functional-errormessage") + "</b></font>"));
    });

    target.append(ul);
}

creme.billing.validateDiscount = function(line) {
    var discount_unit   = parseInt($('select[name=discount_unit]', line).val());
    var discount_total  = parseInt($('select[name=total_discount]', line).val());
    var discount_value  = parseFloat($('input[name=discount]', line).val());
    var unit_price      = parseFloat($('input[name=unit_price]',line).val());
    var quantity        = parseInt($('input[name=quantity]', line).val());

    // TODO gettext
    if (creme.billing.checkPercent($('input[name=discount]', line).val()) !== null && discount_unit == 1) {
        return gettext("Pourcentage invalide.");
    }
    if (discount_total == 1 && discount_unit == 2 && discount_value > unit_price * quantity) {
        return gettext("Le montant de votre remise globale dépasse celui de la ligne sur laquelle vous essayez de l'appliquer.");
    }
    if (discount_total == 2 && discount_unit == 2 && discount_value > unit_price) {
        return gettext("Le montant de votre remise unitaire dépasse celui du produit/service de la ligne sur laquelle vous essayez de l'appliquer.");
    }

    return null;
}

creme.billing.validateDiscountForm = function(line, reload_url) {
    var tbody = line.parents('tbody:first');
    var table_errors = $('td#error_lines', line.parents('table:first'));

    var form_error = creme.billing.validateDiscount(line);

    if (form_error != null) {
        var line_error_message_first = gettext("Sur la ligne ");
        var error_message = line_error_message_first + "<" + $('input#line_number', line).val() + "> : " + form_error;
        $('td#discount_td', line).addClass('discount-functional-error')
                                 .attr('discount-functional-errormessage', error_message);

        creme.billing.printLinesErrors(table_errors, tbody, reload_url);
        return false;
    }

    table_errors.removeClass('line-error');
    $('td#discount_td', line).removeClass('discount-functional-error')
                             .removeAttr('discount-functional-errormessage');

    return true;
}

creme.billing.mapInputs = function (form) {
    var data = {};

    $('input:enabled, select:enabled', form).each(function()
    {
        var key = $(this).attr('name');
        var value = $(this).val()
        if (key !== undefined && value !== undefined)
            data[key] = value;
    });
    return data;
}

creme.billing.submitLine = function(input, reload_url, validator) {
    var line = input.parents('tr.content:first');

    if (validator != null) {
        var error = validator(input.val());
    } else {
        var error = null;
    }

    var isDiscountFormValid = creme.billing.validateDiscountForm(line, reload_url);

    if(error === null) {
        if(isDiscountFormValid) {
            var defaults = {
                'success': function(data, status) {
                    creme.utils.loadBlock(reload_url);
                }
            }
            var datas = creme.billing.mapInputs(line);
            creme.ajax.submit(line, creme.billing.mapInputs(line), defaults);
            $(input).removeClass('creme-field-error');
            $(input).removeAttr('creme-field-errormessage');
        }
    } else {
        $(input).addClass('creme-field-error');
        $(input).attr('creme-field-errormessage', gettext(error));
    }
}