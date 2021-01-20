/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018-2021  Hybird

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
 * Requires : creme, jQuery, creme.utils, creme.ajax, creme.dialogs
 */

(function($) {
"use strict";

creme.reports = creme.reports || {};

creme.reports.ExportReportAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;

        // The export view uses the 'callback_url' feature of inner_popup (maybe only used here).
        // Emulate it for this case.
        // TODO : filterform should be used as select and redirection url build in js.
        creme.dialogs.form(options.filterUrl)
                     .on('frame-activated', function(event, frame) {
                         new creme.reports.PreviewController(options).bind(frame.delegate());
                      })
                     .onFormSuccess(function(event, response, dataType) {
                          self.done(response.content);
                          creme.utils.goTo(response.content);
                      })
                     .onClose(function() {
                          self.cancel();
                      })
                     .open({width: 1024});
    }
});

$(document).on('brick-setup-actions', '.brick.brick-hat-bar', function(e, brick, actions) {
    actions.register('reports-export', function(url, options, data, e) {
        return new creme.reports.ExportReportAction({
            filterUrl: url
        });
    });
});

$(document).on('listview-setup-actions', '.ui-creme-listview', function(e, actions) {
    actions.register('reports-export', function(url, options, data, e) {
        return new creme.reports.ExportReportAction({
            filterUrl: url
        });
    });
});

}(jQuery));
