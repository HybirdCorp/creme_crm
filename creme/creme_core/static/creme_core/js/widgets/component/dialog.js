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

creme.component.Dialog = creme.component.Component.sub({
    _init_: function(options) {
        this.options = $.extend({
            url:       '',
            debug:     false,
            backend:   undefined,
            resizable: true,
            draggable: true,
            width:     640,
            height:    480,
            open:      function() {},
            close:     function() {}
        }, options || {});
    },

    _on_close: function(dialog)
    {
        dialog.dialog('close');
        dialog.dialog('destroy');
        dialog.remove();

        creme.object.invoke(this.options.close);
    },

    _on_open: function(dialog, frame, options)
    {
        var self = this;
        creme.widget.create(frame, options.backend ? {backend: options.backend} : {});
    },

    _populate_buttons: function(buttons, options)
    {
        var self = this;

        buttons[gettext('Close')] = {'name':'close',
                                     'text': gettext('Close'),
                                     'click':function() {self._on_close($(this));}};

        if (options.debug) {
            buttons[gettext('Reload')] = function() {
                                             $('.ui-creme-frame', this).creme().widget().reload();
                                             return false;
                                         };
        }

        return buttons;
    },

    open: function(options)
    {
        var self = this;
        var options = $.extend(this.options, options || {});

        var frame = creme.widget.buildTag($('<div/>'), 'ui-creme-frame', {'url': options.url}, true);
        var buttons = this._populate_buttons({}, options);

        $('<div/>').append(frame)
                   .dialog({buttons:   buttons,
                            title:     options.title,
                            modal:     true,
                            resizable: options.resizable,
                            draggable: options.draggable,
                            width:     options.width,
                            minHeight: options.height,
                            open:      function() {self._on_open($(this), frame, options);}
                           });

        return this;
    }
});


creme.component.FormDialog = creme.component.Dialog.sub({
    _init_: function(options) {
        var options = $.extend({
            success:  function() {},
            validate: function(data, statusText, dataType) {
                return $('form', $('<div>' + data + '</div>')).length == 0;
            }
        }, options || {})

        this._super_(creme.component.Dialog, '_init_', options);
    },

    _on_submit: function(dialog, url)
    {
        var self = this;
        var frame = $('.ui-creme-frame', dialog);
        var form = $('form:first', frame);

        form.attr('action', url);

        frame.creme().widget().submit(form,
                                      function(data, statusText, dataType) {
                                          if (creme.object.invoke(self.options.validate, data, statusText, dataType) == false) {
                                              self._update_buttons("send", dialog, true);
                                          } else {
                                              self._on_close(dialog);
                                              creme.object.invoke(self.options.success, data, statusText, dataType);
                                          }
                                      },
                                      function(data, statusText) {
                                          self._update_buttons("send", dialog, false);
                                      });
    },

    _on_open: function(dialog, frame, options)
    {
        var self = this;

        frame.bind('reloadError', function(data, status) {
            self._update_buttons("send", dialog, false);
        });

        frame.bind('reloadOk', function(data, status) {
            self._update_buttons("send", dialog, true);
        });

        this._super_(creme.component.Dialog, '_on_open', dialog, frame, options);
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

    _populate_buttons: function(buttons, options)
    {
        var self = this;

        this._super_(creme.component.Dialog, '_populate_buttons', buttons, options);

        buttons[gettext('Send')] = {'name':'send',
                                    'text': gettext('Send'),
                                    'click':function() {self._on_submit($(this), options.url);}};

        return buttons;
    }
});


creme.component.Dialogs = {
    openImage: function(image, options, close_cb) {
        var options = $.extend({
            buttons:   {},
            title:     gettext('Canvas image'),
            modal:     true,
            resizable: false,
            draggable: true,
            width:     image.width + 20,
            minHeight: image.height + 20,
            open:      function() {
                           if ($.assertIEVersions(9, 10)) {
                                $(this).parents('.ui-dialog').width(image.width)
                                                             .css('left', (($(window).width() - image.width) / 2) + 'px');
                           }
                       }
        }, options || {})

        $('<div>').css('overflow', 'hidden')
                  .width(image.width)
                  .height(image.height)
                  .append(image)
                  .dialog(options);
    },

    openUrl: function(url, options, close_cb) {
        var dialog = new creme.component.Dialog();

        return dialog.open($.extend({
            url: url,
            close: close_cb
        }, options || {}));
    }
};
