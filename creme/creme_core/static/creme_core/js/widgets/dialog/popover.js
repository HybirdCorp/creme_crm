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

(function($) {
"use strict";

var _DIRECTIONS = ['top', 'left', 'right', 'bottom'];

var _assertDirection = function(direction) {
    if (_DIRECTIONS.indexOf(direction) === -1) {
        throw Error('invalid popover direction ' + direction);
    } else {
        return direction;
    }
};

creme.dialog = creme.dialog || {};

creme.dialog.Popover = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            title:      false,
            closeIfOut: true,
            direction:  'bottom',
            modal:      true
        }, options || {});

        this._events = new creme.component.EventHandler();
        this._options = options;
        this._initFrame(options);
    },

    _initFrame: function(options) {
        var content = $('<div class="popover-content"/>');
        var dialog = this._dialog = $('<div class="popover"><div class="arrow"></div>');

        dialog.append($('<div class="popover-title hidden"/>'));
        dialog.append(content);

        this._glasspane = new creme.dialog.GlassPane().addClass('popover-glasspane');

        this.title(options.title);
        this.direction(options.direction);
    },

    open: function(anchor, options) {
        if (this.isOpened()) {
            throw Error('popover is already opened');
        }

        if (this._options.modal) {
            $('.popover').trigger('modal-close');
        }

        options = this._options = $.extend({}, this._options, options || {});
        anchor = this._anchor = $(anchor);

        var dialog = this._dialog;
        var close = this.close.bind(this);

        dialog.css('visiblility', 'hidden');  // hide dialog before positionning

        $('body').append(dialog);
        this._glasspane.open(dialog);
        this._onclose = function() { close(); };

        this.direction(options.direction || 'bottom');

        dialog.css('visiblility', 'visible');

        dialog.on('modal-close', this._onclose);

        if (options.closeIfOut) {
            this._glasspane.pane().on('mousedown', this._onclose);
        }

        this._events.trigger('opened', [], this);
        return this;
    },

    isOpened: function() {
        return Object.isNone(this._anchor) === false;
    },

    // TODO : never used ? (maybe deprecated by glasspane)
/*
    _closeIfOutside: function(e) {
        var target = $(e.target);
        var isinside = target.closest(this._dialog).length > 0;

        if (isinside === false) {
            this.close();
        }
    },
*/

    _updateDialogPosition: function(dialog, anchor, direction) {
        // offset() is used since it returns the position of the element relative to the document
        // whereas position() is relative to the parent. When adding the popover to the body,
        // we need the absolute position of the anchor in the document.
        var position = $.extend({top: 0, left: 0}, anchor.offset());
        var anchorWidth = anchor.outerWidth() || 0;
        var anchorHeight = anchor.outerHeight() || 0;
        var width = dialog.outerWidth() || 0;
        var height = dialog.outerHeight() || 0;

        switch (direction) {
            case 'bottom':
                position.top += anchorHeight;
                position.left += (anchorWidth - width) / 2;
                // position['min-width'] = anchorWidth;
                break;
            case 'top':
                position.top -= height;
                position.left += (anchorWidth - width) / 2;
                // position['min-width'] = anchorWidth;
                break;
            case 'right':
                position.top += (anchorHeight / 2) - 18;
                position.left += anchorWidth;
                break;
            case 'left':
                position.top += (anchorHeight / 2) - 18;
                position.left -= width;
                break;
        };

        dialog.removeClass(_DIRECTIONS.join(' '));
        dialog.addClass(direction);

        dialog.css(position);
    },

    close: function() {
        this._dialog.off('modal-close', this._onclose);
        this._dialog.detach();

        this._anchor = null;

        this._glasspane.pane().off('mousedown', this._onclose);
        this._glasspane.close();

        this._events.trigger('closed', Array.copy(arguments), this);

        return this;
    },

    options: function() {
        return this._options;
    },

    direction: function(direction) {
        if (direction === undefined) {
            return this._options.direction;
        }

        _assertDirection(direction);

        this._options.direction = direction;

        if (this.isOpened()) {
            this._updateDialogPosition(this._dialog, this._anchor, direction);
        }

        return this;
    },

    title: function(title) {
        if (title === undefined) {
            return $('.popover-title', this._dialog);
        }

        $('.popover-title', this._dialog).toggleClass('hidden', title === false);

        if (Object.isString(title)) {
            $('.popover-title', this._dialog).html(title);
        } else {
            $('.popover-title', this._dialog).empty().append(title);
        }

        return this;
    },

    addClass: function(classname) {
        this._dialog.addClass(classname);
        return this;
    },

    removeClass: function(classname) {
        this._dialog.removeClass(classname);
        return this;
    },

    toggleClass: function(classname, state) {
        this._dialog.toggleClass(classname, state);
        return this;
    },

    content: function() {
        return $('.popover-content', this._dialog);
    },

    fill: function(content) {
        var rendered = Object.isFunc(content) ? content.bind(this)(this._options) : content;

        if (Object.isString(rendered)) {
            $('.popover-content', this._dialog).html(rendered);
        } else {
            $('.popover-content', this._dialog).empty().append(rendered);
        }

        return this;
    },

    toggle: function(anchor, options) {
        if (this.isOpened()) {
            return this.close();
        } else {
            return this.open(anchor, options);
        }
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
        return this;
    }
});
}(jQuery));
