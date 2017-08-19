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
 * Requires : jQuery lib, creme.utils, creme.lv_widget.
 */

(function($) {"use strict";

(function() {
    var detailViewActions = {
        _action_detailview_merge: function(url, options, data) {
            var action = creme.lv_widget.listViewAction(data.selection_url + '?' + $.param({id1: data.id}), {multiple: false});

            action.onDone(function(event, selections) {
                creme.utils.goTo(url + '?' + $.param({id1: data.id, id2: selections[0]}));
            });

            return action;
        },

        _action_detailview_clone: function(url, options, data) {
            return this._action_update_redirect(url, options, data)
        },

        _action_detailview_delete: function(url, options, data) {
            return this._action_update_redirect(url, options, data)
        },

        _action_detailview_restore: function(url, options, data) {
            return this._action_update_redirect(url, options, data)
        }
    };

//    $(document).on('brick-before-bind', '.brick.brick-hat-card', function(e, brick, options) {
    $(document).on('brick-before-bind', '.brick.brick-hat', function(e, brick, options) {
        $.extend(brick, detailViewActions);
    });
})();

}(jQuery));
