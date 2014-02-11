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

creme.dialog = creme.dialog || {};

creme.dialog.Dialog = creme.component.Component.sub({
    _init_: function(options)
    {
        this._events = new creme.component.EventHandler();

        this.options = $.extend({
            url:        undefined,
            backend:    undefined,
            resizable:  true,
            draggable:  true,
            width:      640,
            height:     350,
            scroll:     'frame',
            fitFrame:   true,
            initWidget: true
        }, options || {});

        this._initFrame(this.options);
    },

    _initFrame: function(options)
    {
        var self = this;
        var frame = this._frame = new creme.dialog.Frame({backend: options.backend});

        frame.onCleanup($.proxy(this._onFrameCleanup, this))
             .onUpdate($.proxy(this._onFrameUpdate, this));

        if (options.fitFrame)
        {
            frame.on('fetch-fail submit-fail', function() {
                      self.resizeToDefault();
                      self.position(self.position());
                  });
        }

        frame.bind($('<div>').css('margin', 0).css('padding', 0));
    },
    
    _onFrameCleanup: function() {
        creme.widget.shutdown(this.frame().delegate().children());
    },
    
    _onFrameUpdate: function()
    {
        creme.widget.ready(this.frame().delegate().children());

        if (this.options.fitFrame)
            this.fitToFrameSize();
    },

    _dialogBackground: function() {
        return this._dialog ? $('body > :not(.ui-dialog)') : $([]);
    },

    _destroyDialog: function()
    {
        if (this._dialog)
        {
            this._dialog.dialog('destroy');
            this._dialog.remove();
            this._dialog = undefined;
        }
    },

    _onClose: function(dialog, frame, options)
    {
        this._dialogBackground().toggleClass('ui-dialog-scrollbackground', false);
        this._events.trigger('close', [], this);
    },

    _onOpen: function(dialog, frame, options)
    {
        var self = this;

        this._dialog = dialog;

        if (options.scroll === 'background')
        {
            this._dialog.css('overflow-y', 'hidden');
            this._dialogBackground().toggleClass('ui-dialog-scrollbackground', true);
        }

        if (!Object.isEmpty(options.url)) {
            this.fetch(options.url);
        } else if (!Object.isEmpty(options.html)) {
            this.fill($(options.html));
        }

        this._events.trigger('open', [options], this);

        this._onResize(dialog, frame)
    },

    _onResize: function(dialog, frame)
    {
        var container = dialog.parent('.ui-dialog:first');
        var body = $('> .ui-dialog-content', container);

        this._resizeFrame(body.width() - 5,
                          body.height() - (body.outerHeight() - body.height()))

        this._events.trigger('resize', [frame.delegate().width(), frame.delegate().height()], this);
    },

    _appendButton: function(buttons, name, label, action)
    {
        var self = this;

        buttons[label] = {'name': name,
                          'text': label,
                          'click': function(e) {
                              action.apply(self, [$(this), e]);
                              return false;
                          }
                         };
    },

    _populateButtons: function(buttons, options)
    {
        var self = this;

        this._appendButton(buttons, 'close', gettext('Close'), this.close);
        return buttons;
    },

    _resizeFrame: function(width, height)
    {
        this._frame.delegate().css('width', width - 5)
                              .css('height', height - 5);

        this._frame.resize();
    },

    _resizeDialog: function(width, height)
    {
        if (this._dialog === undefined)
            return;

        var maxWidth = this._dialog.dialog('option', 'maxWidth');
        var maxHeight = this._dialog.dialog('option', 'maxHeight');

        this._dialog.dialog('option', 'width', maxWidth !== false ? Math.min(width, maxWidth) : width);
        this._dialog.dialog('option', 'height', maxHeight !== false ? Math.min(height, maxHeight) : height);
    },

    fitToFrameSize: function()
    {
        var container = $(this._dialog).parent('.ui-dialog:first');
        var body = $('> .ui-dialog-content', container);

        // set frame to default size
        this._frame.delegate().css('width', this.options.width - (container.outerWidth() - body.outerWidth()))
                              .css('height', this.options.height - (container.outerHeight() - body.outerHeight()));

        // eval preferred size of frame elements
        var size = this._frame.preferredSize();
        var preferredWidth = size[0] + (body.outerWidth() - body.width());
        var preferredHeight = size[1] + (body.outerHeight() - body.height());

        // apply this to dialog body
        body.css('width', preferredWidth)
            .css('height', preferredHeight);

        // eval preferred size of dialog with resized body
        var width = body.width();
        var height = container.outerHeight();

        // add a threshold to prevent instability.
        width = Math.abs(width - preferredWidth) < 2 ? preferredWidth : width;
        height = Math.abs(height - preferredHeight) < 2 ? preferredHeight : height;

        this._resizeFrame(size[0], size[1]);
        this._resizeDialog(width, height);
        this.position(this.position());
    },

    center: function() {
        return this.position({my: "center center", at: "center center", of: window});
    },

    position: function(position)
    {
        if (position === undefined)
            return this._dialog ? this._dialog.dialog('option', 'position') : undefined;
        
        this._dialog.dialog('option', 'position', position);
        return this;
    },

    frame: function() {
        return this._frame;
    },

    content: function() {
        return this._frame.delegate();
    },

    resize: function(width, height)
    {
        this._resizeDialog(width, height);
        this._onResize(this._dialog, this._frame.delegate());
    },

    resizeToDefault: function() {
        return this.resize(this.options.width, this.options.height);
    },

    fetch: function(url, options, data, listeners) {
        this._frame.fetch(url, options, data, listeners);
        return this;
    },

    fill: function(data, cb) {
        this._frame.fill(data, cb);
        return this;
    },

    reset: function() {
        this._frame.reset();
        return this;
    },

    dialog: function() {
        return this._dialog;
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

    open: function(options)
    {
        if (this._dialog !== undefined)
            throw Error('dialog already opened !');

        var self = this;
        var options = $.extend(this.options, options || {});
        var frame = this._frame;
        var container = frame.delegate();

        var buttons = this._populateButtons({}, options);

        var content = $('<div/>').append(container);

        var position = {my: "center center", at: "center center", of: window};
        var resizable = options.scroll === 'frame' ? options.resizable : false;
        var draggable = options.scroll === 'frame' ? options.draggable : false;

        this._dialog = content.dialog({buttons:   buttons,
                                       title:     options.title,
                                       modal:     true,
                                       resizable: resizable,
                                       draggable: draggable,
                                       width:     options.width,
                                       height:    options.height,
                                       maxHeight: options.scroll === 'frame' ? options.maxHeight : false,
                                       maxWidth:  options.maxWidth,
                                       position:  position,
                                       closeOnEscape: false,
                                       open:      function() {self._onOpen($(this), frame, options);},
                                       resize:    function() {self._onResize($(this), frame);},
                                       close:     function() {self._onClose($(this), frame, options);}
                                      });

        return this;
    },

    close: function()
    {
        this._destroyDialog();
        return this;
    },

    isOpened: function() {
        return this._dialog != undefined;
    }
});


creme.dialogs = creme.dialogs || {};

creme.dialogs = $.extend(creme.dialogs, {
    image: function(source, options)
    {
        if (Object.isType(source, 'string'))
        {
            var dialog = this.html('');
            var image = document.createElement("img");

            image.onload = function() {dialog.fill($(image)).fitToFrameSize();}
            image.src = source;

            return dialog;
        }

        return this.html(source, options);
    },

    url: function(url, options, data)
    {
        var options = options || {};
        var dialog = new creme.dialog.Dialog(options).fetch(url, {}, data);

        if (options.reloadOnClose) {
            dialog.onClose(function() {creme.utils.reload();});
        }

        return dialog;
    },

    form: function(url, options, data)
    {
        var options = $.extend({compatible: true}, options || {});
        var dialog = new creme.dialog.FormDialog(options);

        if (options.compatible === true)
        {
            var compatibility = function(data, statusText, dataType) {
                return dataType !== 'text/html' ||
                       data.startsWith('<div class="in-popup" closing="true">') ||
                       (data.startsWith('<div class="in-popup"') && data.match(/<form[^>]*>/) === null);
            }

            dialog.validator(compatibility);
        }

        dialog.fetch(url, {}, data);

        if (options.reloadOnSuccess) {
            dialog.onFormSuccess(function() {creme.utils.reload();});
        }

        return dialog;
    },

    html: function(html, options)
    {
        var options = options || {};
        var dialog = new creme.dialog.Dialog($.extend({}, options, {html: html}));

        if (options.reloadOnClose) {
            dialog.onClose(function() {creme.utils.reload();});
        }

        return dialog;
    },

    confirm: function(message, options) {
        return new creme.dialog.ConfirmDialog(message, options);
    },

    choice: function(message, options)
    {
        var options = options || {};
        var data = options.choices || [];
        var selected = options.selected || (data ? data[0] : null);

        var selector = new creme.model.ChoiceRenderer($("<select style='width:100%;'>"), data).redraw().target().val(selected);

        return new creme.dialog.SelectionDialog(options)
                                    .fill($('<p>').html(message).append($('<p>').append(selector)))
                                    .selector(function(frame) {
                                         return $('select', frame).val();
                                     });

        return dialog;
    },

    alert: function(message, options)
    {
        var options = $.extend({title: gettext('Alert'), header: ''}, options || {});
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

    warning: function(message, options)
    {
        var options = $.extend({title: gettext('Warning')}, options || {});
        return this.alert(message, options);
    },

    error: function(message, options, xhr)
    {
        var xhr = $.extend({status: 200}, xhr);
        var header = creme.ajax.localizedErrorMessage(xhr);
        var options = $.extend({title: gettext('Error'), header: header}, options || {});

        return this.alert(message || '', options);
    }
});
