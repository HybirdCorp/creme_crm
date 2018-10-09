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

var waitingSyncActions = {
    'crudity-validate': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
    },

    'crudity-validate-row': function(url, options, data, e) {
        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: [data.id]}, e);
    },

    'crudity-delete': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
    }
};

$(document).on('brick-setup-actions', '.brick.crudity-actions-brick', function(e, brick, actions) {
    actions.registerAll(waitingSyncActions);
});

}(jQuery));
