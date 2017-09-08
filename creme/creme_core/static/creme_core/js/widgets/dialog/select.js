/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.dialog.SelectionDialog = creme.dialog.Dialog.sub({
    _init_: function(options) {
        options = $.extend({
            title:    gettext('Selection'),
            fitFrame: false,
            height:   200
        }, options || {});

        this._super_(creme.dialog.Dialog, '_init_', options);
    },

    validator: function(validator) {
        return Object.property(this, '_validator', validator);
    },

    selector: function(selector) {
        return Object.property(this, '_selector', selector);
    },

    selected: function() {
        var selector = this._selector;
        return Object.isFunc(selector) ? selector.apply(this, [this.content()]) : [];
    },

    ok: function() {
        var validator = this._validator;
        var selected = this.selected();

        if (Object.isFunc(validator) && validator(selected) === false) {
            return this;
        }

        this._destroyDialog();
        this._events.trigger('ok', [selected], this);
        return this;
    },

    _defaultButtons: function(buttons, options) {
        this._appendButton(buttons, 'ok', gettext('Ok'), function(button, e, options) {
                               this.ok();
                           });
        this._appendButton(buttons, 'cancel', gettext('Cancel'), function(button, e, options) {
                               this.close();
                           });

        return buttons;
    },

    onOk: function(cb) {
        this._events.bind('ok', cb);
        return this;
    }
});
}(jQuery));
