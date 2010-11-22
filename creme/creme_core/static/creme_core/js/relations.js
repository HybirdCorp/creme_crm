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
 * Requires : creme, jQuery
 */

if(!creme.relations) creme.relations = {}

creme.relations.handleAddFromPredicateEntity = function(url, predicate_id, subject_id, block_reload_url) {
    var options = {
                'send_button': function(dialog){
                        var lv = $('form', $(dialog));
                        if(lv.size() > 0) {
                            var ids = lv.list_view("getSelectedEntitiesAsArray");
                            if(ids.length == 0 || lv.list_view("countEntities") == 0) {
                                creme.utils.showDialog("Veuillez sélectioner au moins un enregistrement !", {'title':'Erreur'});
                                return;
                            }

                            if(lv.list_view('option','o2m') && lv.list_view("countEntities") > 1) {
                                creme.utils.showDialog("Veuillez sélectioner un seul enregistrement !", {'title':'Erreur'});
                                return;
                            }

                            var infoBoxOptions = {buttons: {
                                                        "Ok": function() {
                                                            if(typeof(block_reload_url) != "undefined")
                                                            {
                                                                $(this).dialog("destroy");
                                                                $(this).remove();
                                                                creme.utils.loadBlock(block_reload_url);
                                                            } else {
                                                                reload(window);
                                                            }
                                                        }
                                                    }
                                                 };
                            creme.ajax.json.post('/creme_core/relation/add_from_predicate/save',
                                                 {
                                                    'entities'    : ids,
                                                    'subject_id'  : subject_id,
                                                    'predicate_id': predicate_id
                                                 },
                                                 function(data){
                                                    creme.utils.showDialog(data, jQuery.extend({'title':'Information'}, infoBoxOptions));
                                                 },
                                                 function(error){
                                                    creme.utils.showDialog(error.request.responseText, jQuery.extend({'title':'Erreur'}, infoBoxOptions));
                                                 }
                                                 ,
                                                 true,
                                                 {dataType:"text"}
                            );
                        }
                        creme.utils.closeDialog(dialog,false);
                  },
                  'send_button_label':"Valider la selection"
                }
    creme.utils.showInnerPopup(url, options);
}

creme.relations.addFromListView = function(lv_selector, url) {
    if($(lv_selector).list_view('ensureSelection')) {
            $(lv_selector).list_view('option', 'entity_separator', ',');

            url += $(lv_selector).list_view('getSelectedEntities') + ',';

            creme.utils.showInnerPopup(url,
                          {
                              beforeClose: function(event, ui, dial) {
                                                $(lv_selector).list_view('reload');
                                            }
                          });
    }
}