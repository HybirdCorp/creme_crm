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
 * Requires : creme, jQuery, creme.utils
 */

creme.filters = {};

creme.filters.getListViewFromCt = function(select) {
    var ct_id = $(select).val();
    var tab_count = $(select).attr('name').split('_');
    var current_count = tab_count[tab_count.length-1]
    //var relation_line_id = $(select).parents('tr').find('[id^="current_relation_id_"]').val();
    var options = {
                    'send_button': function(dialog) {
                            var lv = $('form', $(dialog));
                            if(lv.size() > 0) {
                                var ids = lv.list_view("getSelectedEntities");

                                if(ids == "" || lv.list_view("countEntities") == 0) {
                                    creme.utils.showDialog(gettext("Please select at least one entity."),
                                                           {'title': gettext("Error")});
                                    return;
                                }

                                if(lv.list_view('option', 'o2m') && lv.list_view("countEntities") > 1) {
                                    creme.utils.showDialog(gettext("Please select only one entity."),
                                                           {'title': gettext("Error")});
                                    return;
                                }

                                $('#relation_entity_id_' + current_count).val(ids);
                                creme.ajax.json.post('/creme_core/entity/get_repr/' + ids,
                                                     {},
                                                     function(data) {
                                                         $('#relation_entity_' + current_count).val(data);
                                                     },
                                                     null,
                                                     false,
                                                     {dataType:"text"}
                                );
                            }
                            creme.utils.closeDialog(dialog,false);
                      },
                      'send_button_label': gettext("Validate the selection")
                    }
    creme.utils.showInnerPopup('/creme_core/filter/select_entity_popup/'+ct_id, options);//+'/'+relation_line_id, options);

//    window['select_entity'].relation_line_id = relation_line_id;
}
