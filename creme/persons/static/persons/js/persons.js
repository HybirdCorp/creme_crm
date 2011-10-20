/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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
 * Requires : jQuery, creme
 */

creme.persons = {};

//Copy only in the same order
creme.persons.copyTo = function (from_id, to_id) {
    var $from = $('#' + from_id);
    var $to = $('#' + to_id);
    if($from.size() > 0 && $to.size() > 0) {
        var $to_fill = $to.find('input, textarea, select');
        $from.find('input, textarea, select').each(function(ind){
            $($to_fill[ind]).val($(this).val());
        });
    }
}

// Commented on 7 oct 2010
// creme.persons.retrieveAddress = function(from_node, to_node) {
//     var from_node_val = from_node.val();
//     if(from_node_val != "" && !isNaN(parseInt(from_node_val))) {
//         $.ajax({
//             url: "/persons/address/from_organisation",
//             type: "POST",
//             data: {'entity_id':parseInt(from_node_val), 'ct_id': to_node.ct_id, 'verbose_field':to_node.verbose_field},
//             dataType: "json",
//             success: function(data) {
//                 //$('#'+to_node.id).val(datas[to_node.field]);
//                 var $select = $('#'+to_node.id);
//                 $select.empty();
//                 $select.parent().find('div').remove();
// //                var data = resp.data;
//                 for(var i in data) {
//                     var current = data[i];
//                     $select.append(
//                         $('<option></option>')
//                         .val(current.pk)
//                         .text((current.fields[to_node.verbose_field])?current.fields[to_node.verbose_field]:'Adresse sans nom')
//                     );
//                 }
//                 if(data.length == 0)
//                     $select.append(
//                         $('<option></option>')
//                         .val(0)
//                         .text("Aucune adresse existante ajoutez en une.")
//                     );
// //                $select.val(resp.current);
//                 $select.val(to_node.current);
//                 $select.change();
//             }
//         });
//     }
// }

creme.persons.post_become = function(atag, id_value) {
    $form = $('form', $(atag));
    $input = $('#id_become' , $form);
    $input.attr('value', id_value);

    $form.submit();
}
