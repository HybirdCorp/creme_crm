/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2020  Hybird

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

creme.activities = creme.activities || {};

creme.activities.ExportAsICalAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var selection = this._list.selectedRows();

        if (selection.length < 1) {
            creme.dialogs.warning(gettext('Please select at least a line in order to export.'))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            self.done();
            creme.utils.goTo(options.url, {id: selection});
        }
    }
});

$(document).on('listview-setup-actions', '.ui-creme-listview', function(e, actions) {
    actions.register('activities-export-ical', function(url, options, data, e) {
        return new creme.activities.ExportAsICalAction(this._list, {url: url});
    });
});

}(jQuery));
