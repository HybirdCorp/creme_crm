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

(function($) {
"use strict";

creme.dialog = creme.dialog || {};

var _DIALOG_SCROLLTYPES = ['frame', 'background'];

/*
var _assertScrollType = function(scroll) {
    if (_DIALOG_SCROLLTYPES.indexOf(scroll) === -1) {
        throw new Error('scroll type "${scroll}" is invalid'.template({scroll: scroll}));
    } else {
        return scroll;
    }
};
*/

creme.dialog.Dialog = creme.component.Component.sub({
    _init_: function(options) {
        this._events = new creme.component.EventHandler();
        this._isClosing = false;
        this._deferFrameActivation = false;

        options = this.options = $.extend({
            url:        undefined,
            data:       undefined,
            backend:    undefined,
            resizable:  true,
            draggable:  true,
            width:      640,
            height:     350,
            scroll:     'frame',
            within:     $('.ui-dialog-within-container'),
            fitFrame:   true,
            useFrameTitleBar: true,
            useFrameActions: true,
            closeOnEscape: true,
            scrollbackOnClose: true
        }, options || {});

        this._initFrame(options);
    },

    _initFrame: function(options) {
        var self = this;
        var frame = this._frame = new creme.dialog.Frame({backend: options.backend, autoActivate: false});

        frame.onCleanup($.proxy(this._onFrameCleanup, this))
             .onUpdate($.proxy(this._onFrameUpdate, this));

        if (options.fitFrame) {
            frame.on('fetch-fail submit-fail', function() {
                      self.resizeToDefault();
                      self.position(self.position());
                  });
        }

        frame.bind($('<div>').data('creme-dialog', this)
                             .addClass('ui-creme-dialog-frame'));
    },

    _onFrameCleanup: function() {
        this._events.trigger('frame-cleanup', [this.frame()], this);
    },

    _onFrameUpdate: function() {
        this._events.trigger('frame-update', [this.frame()], this);

        if (this.isOpened()) {
            this._activateFrameContent();
        } else {
            this._deferFrameActivation = true;
        }
    },

    _activateFrameContent: function() {
        if (this._isClosing === true) {
            return;
        }

        if (this.options.useFrameTitleBar) {
//            var dialogHeader = this._dialog.parents('.ui-dialog:first').find('.ui-dialog-titlebar .ui-dialog-title');
            var dialogHeader = this._dialog.parents('.ui-dialog').first().find('.ui-dialog-titlebar .ui-dialog-title');
//            var header = $('.ui-creme-dialog-titlebar:first', this.frame().delegate());
            var header = $('.ui-creme-dialog-titlebar', this.frame().delegate()).first();

            if (header.length > 0) {
                header.appendTo(dialogHeader.empty());
            };
        }

        if (this.options.useFrameActions) {
            this.replaceButtons(this._orderedFrameActionButtons(this.options));
        }

        this.frame().activateContent();

        if (this.options.fitFrame) {
            this.fitToFrameSize();
        }

        this._events.trigger('frame-activated', [this.frame()], this);
    },

    _dialogBackground: function() {
        return this._dialog ? $('body > :not(.ui-dialog)') : $([]);
    },

    _destroyDialog: function() {
        if (this._dialog) {
            this._dialogBackground().toggleClass('ui-dialog-scrollbackground', false);

            this._dialog.dialog('destroy');
            this._dialog.remove();
            this._dialog = undefined;

            creme.utils.scrollBack(this._scrollbackPosition, 'slow');
            this._scrollbackPosition = null;
        }
    },

    _onClose: function(dialog, frame, options) {
        try {
            this._isClosing = true;
            frame.clear();
        } finally {
            this._isClosing = false;
        }

        this._destroyDialog();
        this._events.trigger('close', [options], this);
    },

    _onOpen: function(dialog, frame, options) {
        this._dialog = dialog;

        if (options.scroll === 'background') {
            this._dialog.css('overflow-y', 'hidden');
            this._dialogBackground().toggleClass('ui-dialog-scrollbackground', true);
        }

        if (!Object.isEmpty(options.url)) {
            this.fetch(options.url);
        } else if (!Object.isEmpty(options.html)) {
            this.fill(options.html);
        }

        // If the dialog content is loaded before opening, activation has been deferred.
        // activate it NOW !
        if (this._deferFrameActivation) {
            this._activateFrameContent();
            this._deferFrameActivation = false;
        }

        // HACK : force focus in order to enable escape handling.
        if (options.closeOnEscape && !options.autoFocus) {
            this.focus();
        }

        if (options.scrollbackOnClose) {
            this._scrollbackPosition = creme.utils.scrollBack();
        }

        this._events.trigger('open', [options], this);
    },

    _onResize: function(dialog, frame) {
        var container = this._dialogContainer();
        var body = $('> .ui-dialog-content', container);
        var delegate = frame.delegate();

        delegate.width(body.width() - (delegate.position().left + (body.outerWidth() - body.width())));
        this._events.trigger('resize', [delegate.width(), delegate.height()], this);
    },

    _frameFetchData: function(data) {
        var options = this.options;
        var fetchData = Object.isFunc(options.data) ? options.data.bind(this)(options, data) : options.data || {};
        return $.extend({}, fetchData, data);
    },

    _frameActionLinkButtons: function(options) {
        var self = this;
        var buttons = {};
        var index = 1;

        $('a.ui-creme-dialog-action', this.content()).each(function() {
            var name = $(this).attr('name');

            if (Object.isEmpty(name)) {
                name = "link-" + index;
                ++index;
            }

            var label = $(this).text() || gettext("Action");
            var url = $(this).attr('href');
            self._appendButton(buttons, name, label, function() { this.fetch(url); });
        });

        return buttons;
    },

    _frameActionButtons: function(options) {
        var buttons = this._defaultButtons({}, options);
        return $.extend(buttons, this._frameActionLinkButtons(options));
    },

    _orderedFrameActionButtons: function(options) {
        var buttons = this._frameActionButtons(options);
        return Object.values(buttons).sort(function(a, b) {
            return (a.order || 0) - (b.order || 0);
        });
    },

    _appendButton: function(buttons, name, label, action, options) {
        var self = this;
        var custom_labels = this.options.defaultButtonLabels || {};
        options = options || {};

        var button = $.extend({
                            'name': name,
                            'text': custom_labels[name] || label,
                            'click': function(e) {
                                action.apply(self, [$(this), e, options]);
                                return false;
                            }
                        }, options);

        buttons[name] = button;
        return button;
    },

    _defaultButtons: function(buttons, options) {
        this._appendButton(buttons, 'close', gettext('Close'), function(button, e, options) {
                               this.close();
                           });

        return buttons;
    },

    _removeButton: function(name) {
        this.button(name).detach();
    },

    _updateButtonState: function(name, enabled, focus) {
        var button = this.button(name);

        // HACK : fix jquery ui < 1.8.1 bug that not reset ui-button state.
        button.removeClass('ui-state-focus ui-state-hover ui-state-active');

        button.toggleClass('ui-state-disabled', !enabled);
        button.toggleAttr('disabled', !enabled);

        if ((!this.options.autoFocus && focus === 'auto') || focus === true) {
            button.focus();
        }
    },

    _updateButtonLabel: function(name, label) {
        $('.ui-button-text', this.button(name)).html(label);
    },

    _dialogContainer: function() {
//        return $(this._dialog).parent('.ui-dialog:first');
        return $(this._dialog).parent('.ui-dialog').first();
    },

    _resizeDialog: function(width, height) {
        if (!this.isOpened()) {
            return;
        }

        var maxWidth = this._dialog.dialog('option', 'maxWidth');
        var maxHeight = this._dialog.dialog('option', 'maxHeight');

        var minWidth = this._dialog.dialog('option', 'minWidth');
        var minHeight = this._dialog.dialog('option', 'minHeight');

        width = minWidth > 0 ? Math.max(width, minWidth) : width;
        height = minHeight > 0 ? Math.max(height, minHeight) : height;

        width = maxWidth > 0 ? Math.min(width, maxWidth) : width;
        height = maxHeight > 0 ? Math.min(height, maxHeight) : height;

        this._dialog.dialog('option', 'width', width);
        this._dialog.dialog('option', 'height', height);

        var framePreferredHeight = this._frame.preferredSize()[1];

        if (minHeight > 0) {
            framePreferredHeight = Math.max(minHeight, framePreferredHeight);
        }

        this._frame.delegate().css('min-height', framePreferredHeight)
                              .css('width', 'auto');

        this._frame.overlay().resize();
    },

    fitToFrameSize: function() {
        if (!this.isOpened()) {
            return this;
        }

        var container = this._dialogContainer();
        var body = $('> .ui-dialog-content', container);
        var frame = this._frame.delegate();

        var previousWidth = container.outerWidth();
        var previousHeight = container.outerHeight();

        // set frame to default size
        frame.css('width', (Math.round(this.options.width - (container.outerWidth() - body.width()))));
        var frame_width_padding = frame.position().left + (frame.outerWidth() - frame.width());
        var frame_height_padding = frame.position().top + (frame.outerHeight() - frame.height());

        // eval preferred size of frame elements
        var size = this._frame.preferredSize();
        var preferredWidth = Math.round(size[0] + frame_width_padding + (body.outerWidth() - body.width()));
        var preferredHeight = Math.round(size[1] + frame_height_padding + (body.outerHeight() - body.height()));

        // apply this to dialog body
        body.width(preferredWidth)
            .height(preferredHeight);

        // eval preferred size of dialog with resized body
        var width = container.outerWidth();
        var height = container.outerHeight();

        // add a threshold to prevent instability.
        width = Math.abs(width - previousWidth) < 5 ? previousWidth - 2 : width;
        height = Math.abs(height - previousHeight) < 5 ? previousHeight : height;

        this._resizeDialog(width, height);
        this.position(this.position());

        var maxHeight = this._dialog.dialog('option', 'maxHeight');

        if (height < maxHeight || maxHeight === null) {
            body.height('auto');
        }

        body.css('width', 'auto');

        /*
        console.log('previous:', [previousWidth, previousHeight],
                    'preferred:', [preferredWidth, preferredHeight],
                    'computed:', [width, height],
                    'container:', [container.outerWidth(), container.outerHeight()],
                    'real:', this.length);
        */
    },

    center: function(constraint) {
        if (this.isOpened()) {
            constraint = constraint || {};
            var position = this.cssPosition();

            if (constraint.top > 0 && position.top < constraint.top) {
                this.position({my: 'center top', at: 'center top+' + (constraint.top)});
            } else {
                this.position({my: "center center", at: "center center"});
            }
        }

        return this;
    },

    cssPosition: function() {
        if (this.isOpened()) {
            return this._dialogContainer().position();
        }
    },

    position: function(position) {
        if (position === undefined) {
            return this._dialog ? this._dialog.dialog('option', 'position') : undefined;
        }

        if (Object.isEmpty(this.options.within) === false) {
            position = $.extend({}, position, {
                collision: 'fit',
                within: this.options.within
            });
        }

        this._dialog.dialog('option', 'position', position);
        return this;
    },

    frame: function() {
        return this._frame;
    },

    content: function() {
        return this._frame.delegate();
    },

    buttons: function() {
        return $('.ui-dialog-buttonset', this._dialogContainer());
    },

    button: function(name) {
        return $('button[name="' + name + '"]', this.buttons());
    },

    replaceButtons: function(buttons) {
        this._dialog.dialog('option', 'buttons', buttons);
    },

    resize: function(width, height) {
        this._resizeDialog(width, height);
    },

    resizeToDefault: function() {
        return this.resize(this.options.width, this.options.height);
    },

    size: function() {
        if (this.isOpened()) {
            return {
                width: this._dialog.dialog('option', 'width'),
                height: this._dialog.dialog('option', 'height')
            };
        }
    },

    minSize: function(size) {
        if (size === undefined) {
            if (this.isOpened()) {
                return {
                    width: this._dialog.dialog('option', 'minWidth'),
                    height: this._dialog.dialog('option', 'minHeight')
                };
            }
        } else {
            if (this.isOpened()) {
                this._dialog.dialog('option', 'minWidth', size.width);
                this._dialog.dialog('option', 'minHeight', size.height);
            }

            return this;
        }
    },

    maxSize: function(size) {
        if (size === undefined) {
            if (this.isOpened()) {
                return {
                    width: this._dialog.dialog('option', 'maxWidth'),
                    height: this._dialog.dialog('option', 'maxHeight')
                };
            }
        } else {
            if (this.isOpened()) {
                this._dialog.dialog('option', 'maxWidth', size.width);
                this._dialog.dialog('option', 'maxHeight', size.height);
            }

            return this;
        }
    },

    fetch: function(url, options, data, listeners) {
        this._frame.fetch(url, options, this._frameFetchData(data), listeners);
        return this;
    },

    fill: function(data) {
        this._frame.fill(data);
        return this;
    },

    clear: function() {
        this._frame.clear();
        return this;
    },

    dialog: function() {
        return this._dialog;
    },

    focus: function() {
        this._dialogContainer().focus();
        return this;
    },

    title: function(title) {
        if (title === undefined) {
            return this._dialog.dialog('option', 'title');
        }

        this._dialog.dialog('option', 'title', String(title).decodeHTMLEntities());
        return this;
    },

    onClose: function(closed) {
        this._events.bind('close', closed);
        return this;
    },

    onOpen: function(opened) {
        this._events.bind('open', opened);
        return this;
    },

    on: function(event, listener, decorator) {
        this._events.bind(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.unbind(event, listener);
        return this;
    },

    _onDragStop: function(dialog) {
        this.position(this.position());
    },

    _onResizeStop: function(dialog) {
        this.position(this.position());
    },

    open: function(options) {
        if (this._dialog !== undefined) {
            throw Error('dialog already opened !');
        }

        options = $.extend(this.options, options || {});

        var self = this;
        var frame = this._frame;
        var container = frame.delegate();

        var buttons = $.extend(this._defaultButtons({}, options), options.buttons || {});
        var content = $('<div/>').append(container);
        var scroll = Assert.in(options.scroll, _DIALOG_SCROLLTYPES, 'scroll type "${value}" is invalid');
        var is_framescroll = (scroll === 'frame');
        var position = {};

        if (Object.isEmpty(options.within)) {
            position = {
                my: "center center",
                at: "center center"
            };
        } else {
            position = {
                my: "center center+" + options.within.position().top,
                at: "center center",
                collision: 'fit',
                within: options.within
            };
        }

        var resizable = is_framescroll ? options.resizable : false;
        var draggable = is_framescroll ? options.draggable : false;
        var width = options.minWidth > 0 ? Math.max(options.minWidth, options.width) : options.width;
        var height = options.minHeight > 0 ? Math.max(options.minHeight, options.height) : options.height;
        var title = options.title ? String(options.title).decodeHTMLEntities() : options.title;

        this._dialog = content.dialog({buttons:   Object.values(buttons),
                                       title:     title,
                                       modal:     true,
                                       resizable: resizable,
                                       draggable: draggable,
                                       width:     width,
                                       height:    height,
                                       maxHeight: is_framescroll ? options.maxHeight : false,
                                       maxWidth:  options.maxWidth,
                                       minHeight: options.minHeight,
                                       minWidth:  options.minWidth,
                                       position:  position,
                                       closeOnEscape: options.closeOnEscape,
                                       open:      function() { self._onOpen($(this), frame, options); },
                                       resize:    function() { self._onResize($(this), frame); },
                                       close:     function() { self._onClose($(this), frame, options); },
                                       dragStop:  function() { self._onDragStop($(this)); },
                                       resizeStop: function() { self._onResizeStop($(this)); }
                                      });

        return this;
    },

    close: function() {
        this._onClose(this._dialog, this._frame, this.options);
        return this;
    },

    isOpened: function() {
        return this._dialog !== undefined;
    }
});

/*
creme.dialog.redirect = function(url, from) {
    if (from === undefined) {
        creme.utils.redirect(url);
    }

    var dialog = $(from).parents(".ui-creme-dialog-frame:first").data("creme-dialog");

    if (dialog) {
        dialog.fetch(url);
    }
};
*/

creme.dialog.DialogAction = creme.component.Action.sub({
    _init_: function(options, listeners) {
        this._super_(creme.component.Action, '_init_', this._openPopup, options);
        this._listeners = listeners || {};
    },

    dialog: function() {
        return this._dialog;
    },

    _onClose: function() {
        delete this._dialog;
        this._dialog = undefined;

        this.done();
    },

    _buildPopup: function(options) {
        var self = this;
        options = $.extend(this.options(), options || {});

        this._dialog = new creme.dialog.Dialog(options).onClose(function() { self._onClose(); })
                                                       .on(this._listeners);

        return this._dialog;
    },

    _openPopup: function(options) {
        this._buildPopup(options).open();
    }
});

creme.dialogs = creme.dialogs || {};

creme.dialogs = $.extend(creme.dialogs, {
    image: function(source, options) {
        return new creme.dialog.ImagePopover(options).fillImage(source);
    },

    url: function(url, options, data) {
        options = options || {};
        var dialog = new creme.dialog.Dialog(options).fetch(url, {}, data);

        if (options.reloadOnClose) {
            dialog.onClose(function() {
                creme.utils.reload();
            });
        }

        return dialog;
    },

    form: function(url, options, data) {
        options = $.extend({validator: 'innerpopup'}, options || {});
        var dialog = new creme.dialog.FormDialog(options);

        dialog.fetch(url, {}, data);

        if (options.reloadOnSuccess) {
            dialog.onFormSuccess(function() {
                creme.utils.reload();
            });
        } else if (options.redirectOnSuccess) {
            dialog.onFormSuccess(function(event, response, dataType) {
                var url;

                if (options.redirectOnSuccess === true) {
                    if (response.isHTMLOrElement()) {
                        url = response.data().attr('redirect');
                    } else if (response.isPlainText()) {
                        url = response.content;
                    }
                } else {
                    url = options.redirectOnSuccess;
                }

                if (!Object.isEmpty(url)) {
                    creme.utils.goTo(url);
                }
            });
        }

        return dialog;
    },

    html: function(html, options) {
        options = options || {};
        var dialog = new creme.dialog.Dialog($.extend({}, options, {html: html}));

        if (options.reloadOnClose) {
            dialog.onClose(function() {
                creme.utils.reload();
            });
        }

        return dialog;
    },

    confirm: function(message, options) {
        return new creme.dialog.ConfirmDialog(message, options);
    },

    choice: function(message, options) {
        options = $.extend({
            required: false
        }, options || {});

        var data = options.choices || [];
        var selected = options.selected || (data ? data[0] : null);
        var selector = new creme.model.ChoiceGroupRenderer($("<select style='width:100%;'>"), data).redraw().target();
        var content = $('<div>');

        selector.toggleAttr('required', options.required);

        if (Object.isEmpty(selected.value) === false) {
            selector.val(selected.value);
        } else if (options.required) {
//            selector.val($('option:first', selector).attr('value'));
            selector.val($('option', selector).first().attr('value'));
        }

        if (message) {
            content.append($('<div>').html(message));
        }

        content.append($('<p>').append(selector));

        return new creme.dialog
                        .SelectionDialog(options)
                        .fill(content)
                        .validator(function(value) {
                             return Object.isEmpty(creme.forms.validateHtml5Field(selector));
                        })
                        .selector(function(frame) {
                             return selector.val();
                        });
    },

    alert: function(message, options) {
        options = $.extend({
            title: gettext('Alert'),
            header: ''
        }, options || {});

        var header = options.header || '';
        var content = $('<p class="ui-creme-dialog-warn">').append($('<span class="ui-icon ui-icon-alert">'));

        if (header) {
            content.append($('<span class="header">').html(header))
                   .append($('<p class="message">').html(message));
        } else {
            content.append($('<span class="message">').html(message));
        }

        return this.html(content, options);
    },

    warning: function(message, options) {
        options = $.extend({title: gettext('Warning')}, options || {});
        return this.alert(message, options);
    },

    error: function(message, options, xhr) {
        xhr = $.extend({status: 200}, xhr);
        var header = creme.ajax.localizedErrorMessage(xhr);

        options = $.extend({
            title: gettext('Error'),
            header: header
        }, options || {});

        return this.alert(message || '', options);
    }
});

/*
 * Since jqueryui 1.10 some events are not allowed to get outside the popup.
 * So the custom Chosen widget will not work correctly (needs focus event on search field).
 */
$.widget("ui.dialog", $.ui.dialog, {
    _allowInteraction: function (event) {
        if ($(event.target).closest(".chzn-drop").length) {
            return true;
        }

        return this._super(event);
    }
});
}(jQuery));
