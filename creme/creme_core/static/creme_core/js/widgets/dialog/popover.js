/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2017-2025  Hybird

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

var _DIRECTIONS = ['top', 'left', 'right',
                   'bottom', 'bottom-left', 'bottom-right',
                   'center', 'center-window'];

creme.dialog = creme.dialog || {};

creme.dialog.Popover = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            title:      false,
            closeIfOut: true,
            direction:  'bottom',
            modal:      true,
            scrollbackOnClose: false
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
        anchor = $(anchor);

        if (anchor.length === 0) {
            anchor = $('.ui-dialog-within-container');
        }

        var dialog = this._dialog;
        var close = this.close.bind(this);

        dialog.css('visibility', 'hidden');  // hide dialog before positioning

        this._anchor = anchor;

        $('body').append(dialog);
        this._glasspane.open(dialog);
        this._onclose = function() { close(); };

        this.direction(options.direction || 'bottom');

        dialog.css('visibility', 'visible');

        dialog.on('modal-close', this._onclose);

        if (options.closeIfOut) {
            this._glasspane.pane().on('mousedown', this._onclose);
        }

        if (options.scrollbackOnClose) {
            this._scrollbackPosition = creme.utils.scrollBack();
        }

        this._events.trigger('opened', [], this);
        return this;
    },

    isOpened: function() {
        return Object.isNone(this._anchor) === false;
    },

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
            case 'bottom-left':
                position.top += anchorHeight;
                position.left -= (width - anchorWidth - 18);
                // position['min-width'] = anchorWidth;
                break;
            case 'bottom-right':
                position.top += anchorHeight;
                position.left -= (anchorWidth / 2);
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
            case 'center':
                position.top += (anchorHeight / 2) - 18;
                position.left += (anchorWidth - width) / 2;
                break;
            case 'center-window':
                position.top += (($(window).height() - height) / 2) - 18;
                position.left += ($(window).width() - width) / 2;
                break;
        };

        // We avoid negative coordinates for 'top' & 'left' ; it's not a problem
        // that the popover flows out on the right side of the page (the browser
        // will shrink the popup's width), but it's a problem if the popover
        // flows out on the left side.
        position.top = Math.max(position.top, 0);
        position.left = Math.max(position.left, 0);

        dialog.removeClass(_DIRECTIONS.join(' '));
        dialog.addClass(direction);

        dialog.css(position);
    },

    close: function() {
        if (this.isOpened() === false) {
            return this;
        }

        this._dialog.off('modal-close', this._onclose);
        this._dialog.detach();

        this._anchor = null;

        this._glasspane.pane().off('mousedown', this._onclose);
        this._glasspane.close();

        creme.utils.scrollBack(this._scrollbackPosition, 'slow');
        this._scrollbackPosition = null;

        this._events.trigger('closed', Array.from(arguments), this);

        return this;
    },

    options: function() {
        return this._options;
    },

    direction: function(direction) {
        if (direction === undefined) {
            return this._options.direction;
        }

        Assert.in(direction, _DIRECTIONS, 'invalid popover direction ${value}');

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
            $('.popover-title', this._dialog).text(title.decodeHTMLEntities());
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

        if (this.isOpened()) {
            this._updateDialogPosition(this._dialog, this._anchor, this.direction());
        }

        this._events.trigger('popover-update', [this.content()], this);
        return this;
    },

    toggle: function(anchor, options) {
        if (this.isOpened()) {
            return this.close();
        } else {
            return this.open(anchor, options);
        }
    },

    anchor: function() {
        return this._anchor;
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

creme.dialog.ImagePopover = creme.dialog.Popover.sub({
    _init_: function(options) {
        options = $.extend({
            direction:    'center-window',
            title:        false,
            closeOnClick: true
        }, options || {});

        this._super_(creme.dialog.Popover, '_init_', options);
        this.addClass('popover-picture');
        this._glasspane.addClass('popover-glasspane-picture');

        if (options.closeOnClick) {
            this.content().on('click', this.close.bind(this));
        }
    },

    fill: function(content) {
        this._super_(creme.dialog.Popover, 'fill', content);
        this.content().find('img').toggleClass('no-title', this.options().title === false);
        return this;
    },

    fillImage: function(content) {
        if (Object.isString(content)) {
            var image = document.createElement("img");
            var fill = this.fill.bind(this);

            fill($('<div class="picture-wait">&nbsp;</div>'));

            image.onload = function() {
                fill($(image));
            };

            image.src = content;
            return this;
        }

        return this.fill($(content));
    }
});

creme.dialog.PopoverAction = creme.component.Action.sub({
    _init_: function(options, listeners) {
        this._super_(creme.component.Action, '_init_', this._open, options);
        this._listeners = listeners || {};
    },

    _build: function(options) {
        var self = this;
        var popover = new creme.dialog.Popover(options);

        popover.on('closed', function() {
            self.done();
        }).fill(
            options.content || ''
        ).on(
            self._listeners
        );

        return popover;
    },

    _open: function(options) {
        options = $.extend(this.options(), options || {});
        this._build(options).open(options.target);
    }
});

creme.dialog.PopoverAction.fromTarget = function(target, options) {
    /*
        Opens a popover at the given DOM/jquery target element.
        Some arguments like the title and the content are extracted directly from the element :
         - <a content-href="#my_id">
              Gets the body from another tag outside the link.
         - <a><script type="text/html"></script></a>
              Gets the body from the script tag within the link. Works HTML links
         - <a title=""> or <a summary="">
              Gives the popover title.
         - <a><details></details></a>
              Gets the body from the details tag (backward compatibility). DOES NOT work HTML links
    */
    target = $(target);

    var contentHref = target.data('contentHref');
    var content = contentHref ? $(contentHref).text() : target.find('script[type$="html"]').text();
    var title = target.data('title') || target.find('summary').text();

    // Keeps compatibility with older way of creating popover
    if (Object.isEmpty(content)) {
        content = target.find('details').html();
    }

    options = Object.assign({
        content: content,
        title: title
    }, options || {}, {
        target: target
    });

    return new creme.dialog.PopoverAction(options);
};

}(jQuery));
