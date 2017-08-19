/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015  Hybird

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

creme.dialogs = creme.dialogs || {};

creme.dialogs.Popover = creme.component.Component.sub({
    _init_: function(options)
    {
        var options = $.extend({
            choices:    [],
            title:      '',
            closeIfOut: true,
            direction:  'bottom',
            content:    '',
            modal:      true
        }, options || {});

        this._events = new creme.component.EventHandler();
        this._options = options;
        this._initFrame(options);
    },

    _initFrame: function(options)
    {
        var content = $('<div class="popover-content"/>');
        content.html(Object.isFunc(options.content) ? options.content.bind(this)(options) : options.content);

        var dialog = this._dialog = $('<div class="popover %s"><div class="arrow"></div>'.format(options.direction));

        if (options.title) {
            dialog.append($('<div class="popover-title"/>').html(options.title));
        }

        dialog.append(content);
        this._glasspane = new creme.dialogs.GlassPane().addClass('popover-glasspane');
    },

    selectAndClose: function(value)
    {
        this._events.trigger('ok', [value]);
        this.close();
    },

    open: function(anchor, options)
    {
        if (this.isOpened()) {
            return;
        }

        if (this._options.modal) {
            $('.popover').trigger('modal-close');
        }

        var options = $.extend(this._options, options || {});
        var direction = options.direction || 'bottom';

        var anchor = this._anchor = $(anchor);

        // offset() is used since it returns the position of the element relative to the document
        // whereas position() is relative to the parent. When adding the popover to the body,
        // we need the absolute position of the anchor in the document.
        var position = anchor.offset();

        var width = anchor.outerWidth() || 0;
        var height = anchor.outerHeight() || 0;
        var dialog = this._dialog;

        $('body').append(this._dialog);

        if (direction === 'bottom') {
            position.top += height;
            position.left -= width / 2;
            position['min-width'] = width;
        } else if (direction === 'top') {
            position.bottom += height;
            position.left -= width / 2;
            position['min-width'] = width;
        } else if (direction === 'right') {
            position.top += (height / 2) - 18;
            position.left += width;
        } else if (direction === 'left') {
            position.top -= (height / 2) - 18;
            position.left -= width;
        }

        dialog.css(position);
        this._glasspane.open(dialog);

        dialog.on('modal-close', this.close.bind(this));

        if (options.closeIfOut) {
            this._glasspane.pane().on('mousedown', this.close.bind(this));
        }

        this._events.trigger('opened', [], this);
        return this;
    },

    isOpened: function() {
        return Object.isNone(this._anchor) === false;
    },

    _closeIfOutside: function(e)
    {
        var target = $(e.target);
        var isinside = target.closest(this._dialog).length > 0;

        if (isinside === false) {
            this.close();
        }
    },

    close: function()
    {
        this._dialog.detach();
        this._anchor = null;
        this._glasspane.close();
        this._events.trigger('closed', [], this);

        return this;
    },

    fill: function(content)
    {
        var options = this._options;
        var content = content || options.content;
        $('.popover-content', this._dialog).html(Object.isFunc(content) ? content.bind(this)(options) : content);

        return this;
    },

    toggle: function(anchor, options)
    {
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
    },

    onOk: function(listener, decorator) {
        return this.on('ok', listener, decorator);
    }
});
