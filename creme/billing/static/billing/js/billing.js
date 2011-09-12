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