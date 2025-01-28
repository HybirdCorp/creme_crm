/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2018-2025  Hybird

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

creme.action = creme.action || {};

creme.action.DefaultActionBuilderRegistry = creme.component.FactoryRegistry.sub({
    _redirectAction: function(url, options, data) {
        return new creme.component.Action(function() {
            options = options || {};

            var locationUrl = creme.utils.locationRelativeUrl();

            // apply ${location} template to url.
            var resolvedUrl = url.template($.extend({
                location: locationUrl
            }, data || {}));

            // comeback is a shortcut for ?callback_url=${location}
            if (options.comeback) {
                resolvedUrl = _.toRelativeURL(resolvedUrl).updateSearchData({
                    callback_url: locationUrl
                }).toString();
            }

            creme.utils.goTo(resolvedUrl);
            this.done();
        });
    },

    _warningAction: function(message) {
        return new creme.component.Action(function() {
            var self = this;
            creme.dialogs.warning(message)
                         .onClose(function() {
                             self.fail();
                          })
                         .open();
        });
    },

    _postQueryAction: function(url, options, data) {
        options = $.extend({action: 'post'}, options || {});
        return creme.utils.ajaxQuery(url, options, data);
    },

    _reloadAction: function(url, options, data) {
        return new creme.component.Action(function() {
            creme.utils.reload();
            this.done();
        });
    },

    _build_redirect: function(url, options, data) {
        return this._redirectAction(url, options, data);
    }
});

}(jQuery));
