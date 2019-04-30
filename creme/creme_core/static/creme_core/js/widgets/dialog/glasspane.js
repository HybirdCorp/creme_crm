/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2019  Hybird

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

creme.dialog = creme.dialog || {};

creme.dialog.GlassPane = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            debug: false,
            modal: false
        }, options || {});

        this._events = new creme.component.EventHandler();
        this._options = options;
        this._opened = false;
        this._initFrame(options);
    },

    _initFrame: function(options) {
        var pane = this._pane = $('<div class="glasspane">');

        // TODO : useful ?
        if (options.debug) {
            pane.attr('data-debug', '');
        }
    },

    pane: function() {
        return this._pane;
    },

    addClass: function() {
        this._pane.addClass.apply(this._pane, arguments);
        return this;
    },

    removeClass: function() {
        this._pane.removeClass.apply(this._pane, arguments);
        return this;
    },

    toggleClass: function() {
        this._pane.toggleClass.apply(this._pane, arguments);
        return this;
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    open: function(anchor) {
        if (this.isOpened()) {
            throw Error('glasspane is already opened');
        }

        var pane = this._pane;

        if (anchor) {
            var zindex = anchor.css('z-index') - 1;

            if (zindex > 0) {
                pane.css('z-index', zindex);
            }
        }

        $('body').append(pane);
        this._opened = true;

        this._pane.trigger('glasspane-opened', this);
        this._events.trigger('opened', [], this);

        return this;
    },

    isOpened: function() {
        return this._opened;
    },

    close: function() {
        if (this.isOpened() === false) {
            return this;
        }

        this._pane.detach();
        this._opened = false;

        this._pane.trigger('glasspane-closed', this);
        this._events.trigger('closed', [], this);


        return this;
    },

    toggle: function(anchor) {
        if (this.isOpened()) {
            return this.close();
        } else {
            return this.open(anchor);
        }
    }
});
}(jQuery));
