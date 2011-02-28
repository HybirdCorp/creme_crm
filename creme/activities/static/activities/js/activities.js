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

creme.activities = {};

creme.activities.ajax = {};

creme.activities.select_one = function(url, ct_id) {
    var me = this;

    this.okDialogHandler = function(ui) {
        url += '&entity_relation_type=' + $(ui).find('select').val();
        $(ui).dialog("destroy");
        $(ui).remove();
        window.location.href = url;
    }

    creme.ajax.json.post('/activities/get_relationtype_choices', {'ct_id': ct_id},
        function(data) {
            var options = creme.forms.Select.optionsFromData(data, 'predicate', 'pk');
            var $select = creme.forms.Select.fill($('<select/>'), options, options[0][0]);
            var buttons = {};

            buttons[gettext("Ok")] = function() {
                    me.okDialogHandler($(this))
                }

            creme.utils.showDialog($select, {title: '', modal: true, buttons: buttons });
         });
}
