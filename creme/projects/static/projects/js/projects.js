/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018-2024  Hybird

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


(function($) {
"use strict";

creme.projects = creme.projects || {};

$(document).on('listview-setup-actions', '.ui-creme-listview', function(e, actions) {
    actions.register('projects-close', function(url, options, data, e) {
        var list = this._list;
        options = $.extend({
            action: 'post',
            confirm: gettext('Do you really want to close this project?'),
            warnOnFail: true
        }, options || {});

        var action = creme.utils.ajaxQuery(url, options, data);

        action.onDone(function() {
            list.reload();
        });

        return action;
    });
});

}(jQuery));
