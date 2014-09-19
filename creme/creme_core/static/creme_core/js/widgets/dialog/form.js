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

creme.dialog.FormDialog = creme.dialog.Dialog.sub({
    _init_: function(options)
    {
        var self = this;
        var options = $.extend({
                autoFocus: true,
                submitOnKey: 13
            }, options || {});

        this._super_(creme.dialog.Dialog, '_init_', options);

        var validator = options.validator || function(data, statusText, dataType) {
            return dataType !== 'text/html' || data.match(/<form[^>]*>/) === null;
        };

        this.validator(validator);

        var update_buttons = function() {
            self._updateButtonState("send", false);
            self._updateButtonState("cancel", true, false);
        };

        this.frame().on('before-submit before-fetch', update_buttons);

        this._submitListeners = {
            done: $.proxy(this._onSubmitDone, this),
            fail: $.proxy(this._onSubmitFail, this)
        };

        this._submitKeyCb = $.proxy(this._onSubmitKey, this);
    },

    validator: function(validator)
    {
        if (validator === undefined)
            return this._validator;

        if (!Object.isFunc(validator))
            throw new Error('validator is not a function');

        this._validator = validator;
        return this;
    },

    _validate: function(data, statusText, dataType)
    {
        var validator = this.validator();
        return !Object.isFunc(validator) || validator(data, statusText, dataType);
    },

    submit: function()
    {
        var self = this;
        var dialog = this.dialog();
        var form = $('form:first', this.content());

        this.frame().submit('', {}, form, this._submitListeners);
        return this;
    },

    _onFrameUpdate: function(event, data, dataType, action)
    {
        if (action !== 'submit')
            this._super_(creme.dialog.Dialog, '_onFrameUpdate', event, data, dataType, action);

        if (this.options.autoFocus) {
            var autofocus = $('[autofocus]:tabbable:first', this._frame.delegate());

            if (autofocus.length > 0) {
                autofocus.focus();
            } else {
                $(':tabbable:first', this._frame.delegate()).focus();
            }
        } else {
            $(':tabbable', this._frame.delegate()).blur();
        }
    },

    _onSubmitDone: function(event, data, statusText, dataType)
    {
        if (this._validate(data, statusText, dataType)) {
            this._destroyDialog();
            this._events.trigger('form-success', [data, statusText, dataType], this);
            return;
        }

        this._super_(creme.dialog.Dialog, '_onFrameUpdate', event, data, dataType, 'submit');
        this._updateButtonState("send", true, 'auto');
        this._updateButtonState("cancel", true);

        this._events.trigger('form-error', [data, statusText, dataType], this);
    },

    _onSubmitFail: function(event, data, statusText) {
        this._updateButtonState("send", false);
        this._updateButtonState("cancel", true, true);
    },

    _onSubmitKey: function(e) {
        if (e.keyCode === this.options.submitOnKey && $(e.target).is(':not(textarea)')) {
            e.preventDefault();
            this.submit();
        }
    },

    _onClose: function(dialog, frame, options)
    {
        if (options.submitOnKey) {
            frame.delegate().unbind('keypress', this._submitKeyCb);
        }

        this._super_(creme.dialog.Dialog, '_onClose', dialog, frame, options);
    },

    _onOpen: function(dialog, frame, options)
    {
        var self = this;

        frame.onFetchFail(function(data, status) {
                  self._updateButtonState("send", false);
                  self._updateButtonState("cancel", true, true);
              })
              .onFetchDone(function(data, status) {
                  self._updateButtonState("send", true, 'auto');
                  self._updateButtonState("cancel", true);
              });

        if (options.submitOnKey) {
            frame.delegate().bind('keypress', this._submitKeyCb);
        }

        this._super_(creme.dialog.Dialog, '_onOpen', dialog, frame, options);
    },

    _updateButtonState: function(name, enabled, focus)
    {
        var button = this.button(name);

        // HACK : fix jquery ui < 1.8.1 bug that not reset ui-button state.
        button.removeClass('ui-state-focus ui-state-hover ui-state-active');

        button.toggleClass('ui-state-disabled', !enabled);
        button.toggleAttr('disabled', !enabled);

        if ((!this.options.autoFocus && focus === 'auto') || focus === true)
            button.focus();
    },

    _updateButtonLabel: function(name, label) {
        $('.ui-button-text', this.button(name)).html(label);
    },

    _populateButtons: function(buttons, options)
    {
        this._appendButton(buttons, 'send', gettext('Save'), this.submit);
        this._appendButton(buttons, 'cancel', gettext('Cancel'), this.close);

        return buttons;
    },

    onFormSuccess: function(success)
    {
        this._events.bind('form-success', success);
        return this;
    },

    onFormError: function(error)
    {
        this._events.bind('form-error', error);
        return this;
    }
});


creme.dialog.FormDialogAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._openPopup, options);
    },

    _onSubmit: function(data, statusText, dataType)
    {
        if ($.assertIEVersions(7, 8, 9)) {
            data = data.endsWith('</json>') || data.endsWith('</JSON>') ? data.substr(0, data.length - '</json>'.length) : data;
        }

        this.done(data);
    },

    _openPopup: function(options)
    {
        var self = this;

        new creme.dialog.FormDialog(options).onFormSuccess(function(event, data) {self._onSubmit(data);})
                                            .onClose(function() {self.cancel();})
                                            .open();
    }
});
