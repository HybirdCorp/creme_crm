/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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
 * Requires : jQuery, Creme
 */

(function($) {
"use strict";

creme.cti = {};

creme.cti.PhoneCallAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var call = creme.ajax.query(options.ctiServerUrl);

        call.onFail(function() {
            creme.dialogs.warning(gettext("Unable to start the phone call. Please check your CTI configuration."))
                         .onClose(function() { self.fail(); })
                         .open();
        }).onDone(function() {
            var query = creme.ajax.query(options.saveCallUrl);

            query.onFail(function() {
                // TODO: better error message (wait for jsonify improvement)
                creme.dialogs.warning(gettext("Failed to save the phone call."))
                             .onClose(function() { self.fail(); })
                             .open();
            }).onDone(function(event, message) {
                creme.dialogs.html($('<p>').append(message), {'title': gettext("Phone call")})
                             .onClose(function() { self.done(); })
                             .open();
            }).post({
                entity_id: options.callerId
            });
        }).get({
            n_tel: options.number
        });
    }
});

creme.cti.phoneCall = function(external_url, creme_url, number, entity_id) {
    var action = new creme.cti.PhoneCallAction({
        ctiServerUrl: external_url,
        saveCallUrl: creme_url,
        number: number,
        callerId: entity_id
    });

    return action.start();
};

}(jQuery));
