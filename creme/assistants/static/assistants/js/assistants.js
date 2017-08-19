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

(function($) {"use strict";

creme.assistants = creme.assistants || {};

creme.assistants.validateEntity = function(form, checkbox_id, reload_url) {
    console.warn('creme.assistants.validateEntity() is deprecated ; use the new brick action system instead.');

    if (!$('#' + checkbox_id).is(':checked')) {
        creme.dialogs.warning(gettext("Check the box if you consider as treated"))
                     .open();
    } else {
        creme.ajax.jqueryFormSubmit($(form), function() {
            creme.blocks.reload(reload_url);
        });
    }
};

}(jQuery));
