/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017  Hybird

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
 * Requires : creme, jQuery, creme.bricks
 */

(function($) {
"use strict";

creme.crudity = {};

(function() {
    /* TODO: factorise with 'emails.js' */
    var emptySelectionAction = function(message) {
        return new creme.component.Action(function() {
            var self = this;
            creme.dialogs.warning(message)
                         .onClose(function() {self.fail();})
                         .open();
        });
    };

    var waitingSyncActions = {
        _action_crudity_validate: function(url, options, data, e) {
            var values = $(data.selector).getValues();

            if (values.length === 0) {
                return emptySelectionAction(gettext('Nothing is selected.'));
            }

            return this._action_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
        },

        _action_crudity_delete: function(url, options, data, e) {
            var values = $(data.selector).getValues();

            if (values.length === 0) {
                return emptySelectionAction(gettext('Nothing is selected.'));
            }

            return this._action_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
        },
    };

    $(document).on('brick-before-bind', '.brick.crudity-actions-brick', function(e, brick) {
        $.extend(brick, waitingSyncActions);
    });
}());

}(jQuery));
