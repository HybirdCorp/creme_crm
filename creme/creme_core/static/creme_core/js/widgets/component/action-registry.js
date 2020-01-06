/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2018-2019  Hybird

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
        var context = $.extend({
            location: window.location.href.replace(/.*?:\/\/[^\/]*/g, '') // remove 'http://host.com'
        }, data || {});

        return new creme.component.Action(function() {
            creme.utils.goTo(creme.utils.templatize(url, context).render());
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
    }
});

}(jQuery));
