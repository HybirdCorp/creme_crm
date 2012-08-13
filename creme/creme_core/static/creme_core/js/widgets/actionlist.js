/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

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

creme.widget.ActionButtonList = creme.widget.declare('ui-creme-actionbuttonlist', {
    options: {
        debug: true
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;
        var delegate = creme.widget.create(self.delegate(element));

        self.actions(element).each(function() {
            $(this).bind('click', function() {
                self._handle_action(element, $(this));
                return false;
            });
        });

        element.addClass('widget-ready');
    },

    actions: function(element) {
        return $('> li > button.ui-creme-actionbutton', element);
    },

    action: function(element, index) {
        return $('> li > button.ui-creme-actionbutton:nth(' + index + ')', element);
    },

    delegate: function(element) {
        return $('> li.delegate > .ui-creme-widget', element);
    },

    dependencies: function(element)
    {
        var delegate = this.delegate(element).creme().widget();
        return creme.object.delegate(delegate, 'dependencies') || [];
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        var delegate = this.delegate(element).creme().widget();
        return creme.object.delegate(delegate, 'reload', data, cb, error_cb, sync);
    },

    val: function(element, value)
    {
        var delegate = this.delegate(element).creme().widget();
        return creme.object.delegate(delegate, 'val', value) || '';
    },

    cleanedval: function(element)
    {
        var delegate = this.delegate(element).creme().widget();
        return creme.object.delegate(delegate, 'cleanedval') || null;
    },

    _on_action_success: function(element, data, statusText, dataType)
    {
        var self = this;
        var delegate = self.delegate(element).creme().widget();
        var item = creme.widget.parseval(data, creme.ajax.json.parse);

        if (creme.object.isempty(delegate))
            return;

        if (item != null) {
            delegate.update(data);
        } else {
            delegate.reload();
        }
    },

    _handle_action: function(element, button)
    {
        var self = this;
        var action = creme.widget.parseopt(button, {action:'popup'}).action;

        var handler = self['_handle_action_' + action];

        if (handler !== undefined)
            self['_handle_action_' + action](element, button);

        return false;
    },

    _handle_action_reset: function(element, button)
    {
        var options = creme.widget.parseopt(button, {value: ''});
        this._on_action_success(element, {value:options.value}, 'success');
    },

    _handle_action_popup: function(element, button)
    {
        var options = creme.widget.parseopt(button, {popupResizable: true,
                                                     popupDraggable: true,
                                                     popupWidth: window.screen.width / 2,
                                                     popupHeight: 356,
                                                     url: '',
                                                     title: ''});

        this._open_popup(element, button, options);
    },

    _handle_submit_popup: function(element, dialog, url)
    {
        var self = this;
        var frame = $('.ui-creme-frame', dialog);
        var form = $('form:first', frame);

        form.attr('action', url);

        frame.creme().widget().submit(form,
                                      function(data, statusText, dataType) {
                                          if (dataType === 'text/json')
                                          {
                                              self._close_popup(element, dialog);

                                              element.trigger('actionSuccess', [data, statusText, dataType]);
                                              self._on_action_success(element, data, statusText, dataType);
                                              return;
                                          }

                                          self._update_popup_button(element, "send", dialog, ($('form', $(data)).length > 0));
                                      },
                                      function(data, statusText) {
                                          self._update_popup_button(element, "send", dialog, false);
                                      });
    },

    _handle_cancel_popup: function(element, dialog)
    {
        this._close_popup(element, dialog);
        element.trigger('actionCancel');
    },

    _handle_open_popup: function(element, dialog, frame)
    {
        var self = this;
        creme.widget.ready(dialog);

        frame.bind('reloadError', function(data, status) {
            self._update_popup_button(element, "send", dialog, false);
        });

        frame.bind('reloadOk', function(data, status) {
            self._update_popup_button(element, "send", dialog, true);
        });
    },

    _update_popup_button: function(element, name, dialog, enabled)
    {
        var button = $('.ui-dialog-buttonset button[name="' + name + '"]', dialog.parent());

        button.toggleClass('ui-state-disabled', !enabled);

        if (enabled)
            button.removeAttr('disabled');
        else
            button.attr('disabled', 'true');
    },

    _close_popup: function(element, dialog)
    {
        dialog.dialog('close');
        dialog.dialog('destroy');
        dialog.remove();
    },

    _open_popup: function(element, button, options)
    {
        var self = this;
        var frame = creme.widget.buildTag($('<div/>'), 'ui-creme-frame', {'url': options.url}, true);

        var buttons = {};
        buttons[gettext('Close')] = {'name':'close',
                                     'text': gettext('Close'),
                                     'click':function() {self._handle_cancel_popup(element, $(this));}};
        buttons[gettext('Send')] = {'name':'send',
                                    'text': gettext('Send'),
                                    'click':function() {self._handle_submit_popup(element, $(this), options.url);}};

        if (options.debug) {
            buttons[gettext('Reload')] = function() {
                                             $('.ui-creme-frame', this).creme().widget().reload();
                                             return false;
                                         };
        }

        $('<div/>').append(frame)
                   .dialog({buttons:   buttons,
                            title:     options.title,
                            modal:     true,
                            resizable: options.popupResizable,
                            draggable: options.popupResizable,
                            width:     options.popupWidth,
                            minHeight: options.popupHeight,
                            open:      function() {self._handle_open_popup(element, $(this), frame);}
                           });
    }
});
