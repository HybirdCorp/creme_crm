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

creme.component.Action = creme.component.Component.sub({
    _init_: function(action, options)
    {
        this._events = new creme.component.EventHandler();
        this._options = options || {};
        this._status = 'done';
        this._action = Object.isFunc(action) ? action : this.done;
    },

    start: function(options)
    {
        var self = this;

        if (this.isRunning() === true)
            return this;

        try {
            this._status = 'run';
            this._action.apply(this, Array.copy(arguments));
        } catch(e) {
            this.fail(e);
        }

        return this;
    },

    done: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'done';
        this._events.trigger('done', Array.copy(arguments), this);
        return this;
    },

    fail: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'fail';
        this._events.trigger('fail', Array.copy(arguments), this);
        return this;
    },

    cancel: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'cancel';
        this._events.trigger('cancel', Array.copy(arguments), this);
        return this;
    },

    action: function(data)
    {
        var self = this;
        var action = (data === undefined || Object.isFunc(data)) ? data : function() {self.done(data);};

        return Object.property(this, '_action', action);
    },

    bind: function(key, listener) {
        this._events.bind(key, listener);
        return this;
    },

    onDone: function(success) {
        return this.bind('done', success);
    },

    onCancel: function(canceled) {
        return this.bind('cancel', canceled);
    },

    onFail: function(error) {
        return this.bind('fail', error);
    },

    isRunning: function() {
        return this._status === 'run';
    },

    status: function() {
        return this._status;
    },

    options: function(options) {
        return Object.property(this, '_options', options);
    },

    after: function(source)
    {
        var self = this;

        source.onDone(function(event, data) {
            self.start(data);
        });

        source.onFail(function(event, data) {
            self.fail(data);
        });

        source.onCancel(function(event, data) {
            self.cancel(data);
        });

        return this;
    }
});


creme.component.FormDialogAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._open_popup, options);
    },

    _on_popup_submit: function(dialog, url)
    {
        var self = this;
        var frame = $('.ui-creme-frame', dialog);
        var form = $('form:first', frame);

        form.attr('action', url);

        frame.creme().widget().submit(form,
                                      function(data, statusText, dataType) {
                                          if ($.assertIEVersions(7, 8, 9)) {
                                              data = data.endsWith('</json>') || data.endsWith('</JSON>') ? data.substr(0, data.length - '</json>'.length) : data;
                                              dataType = new creme.object.JSON().isJSON(data) ? 'text/json' : dataType;
                                          }

                                          if (dataType === 'text/json')
                                          {
                                              self._close_popup(dialog);
                                              self.done(data);
                                              return;
                                          }

                                          self._update_buttons("send", dialog, ($('form', $(data)).length > 0));
                                      },
                                      function(data, statusText) {
                                          self._update_buttons("send", dialog, false);
                                      });
    },

    _on_popup_cancel: function(dialog)
    {
        this._close_popup(dialog);
        this.cancel();
    },

    _on_popup_open: function(dialog, frame)
    {
        var self = this;
        creme.widget.ready(dialog);

        frame.bind('reloadError', function(data, status) {
            self._update_buttons("send", dialog, false);
        });

        frame.bind('reloadOk', function(data, status) {
            self._update_buttons("send", dialog, true);
        });
    },

    _update_buttons: function(name, dialog, enabled)
    {
        var button = $('.ui-dialog-buttonset button[name="' + name + '"]', dialog.parent());

        button.toggleClass('ui-state-disabled', !enabled);

        if (enabled)
            button.removeAttr('disabled');
        else
            button.attr('disabled', 'true');
    },

    _close_popup: function(dialog)
    {
        dialog.dialog('close');
        dialog.dialog('destroy');
        dialog.remove();
    },

    _open_popup: function(options)
    {
        var self = this;
        var frame = creme.widget.buildTag($('<div/>'), 'ui-creme-frame', {'url': options.url}, true);

        var buttons = {};
        buttons[gettext('Close')] = {'name':'close',
                                     'text': gettext('Close'),
                                     'click':function() {self._on_popup_cancel($(this));}};
        buttons[gettext('Send')] = {'name':'send',
                                    'text': gettext('Send'),
                                    'click':function() {self._on_popup_submit($(this), options.url);}};

        $('<div/>').append(frame)
                   .dialog({buttons:   buttons,
                            title:     options.title,
                            modal:     true,
                            resizable: options.popupResizable,
                            draggable: options.popupResizable,
                            width:     options.popupWidth,
                            minHeight: options.popupHeight,
                            open:      function() {self._on_popup_open($(this), frame);}
                           });
    }
});