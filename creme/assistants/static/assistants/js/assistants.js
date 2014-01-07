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

creme.assistants = creme.assistants || {};

// TODO : a simple checkbox change with confirmation may do the same work ?
creme.assistants.validateEntity = function(form, checkbox_id, reload_url) {
    if (!$('#' + checkbox_id).is(':checked')) {
        creme.dialogs.warning(gettext("Check the box if you consider as treated"))
                     .open();
    } else {
        creme.ajax.jqueryFormSubmit($(form), function() {creme.blocks.reload(reload_url);});
    }

/*
    var checked = document.getElementById(checkbox_id);
    if (checked.checked == false) {
        creme.utils.showDialog('<p>' + gettext("Check the box if you consider as treated") + '</p>',
                               {'title': gettext("Error")}, 'error');
    } else {
//        form.submit();
        creme.ajax.submit(form, {}, {'success': function(){creme.blocks.reload(reload_url);}});
    }
*/
}
