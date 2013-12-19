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
        var options = options || {};

        this._super_(creme.dialog.Dialog, '_init_', options);

        var validator = options.validator || function(data, statusText, dataType) {
            return dataType !== 'text/html' || data.match(/<form[^>]*>/) === null;
        };

        this.validator(validator);

        var update_buttons = function() {
            self._updateButtons("send", self.dialog(), false);
        };

        this.frame().on('before-submit before-fetch', update_buttons);

        this._submitListeners = {
            done: $.proxy(this._onSubmitDone, this),
            fail: $.proxy(this._onSubmitFail, this)
        };
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
    },

    _onSubmitDone: function(event, data, statusText, dataType)
    {
        if (this._validate(data, statusText, dataType)) {
            this._destroyDialog();
            this._events.trigger('form-success', [data, statusText, dataType], this);
            return;
        }

        this._super_(creme.dialog.Dialog, '_onFrameUpdate', event, data, dataType, 'submit');
        this._updateButtons("send", this.dialog(), true);
        this._events.trigger('form-error', [data, statusText, dataType], this);
    },

    _onSubmitFail: function(event, data, statusText) {
        this._updateButtons("send", this.dialog(), false);
    },

    _onOpen: function(dialog, frame, options)
    {
        var self = this;

        frame.onFetchFail(function(data, status) {
                  self._updateButtons("send", dialog, false);
              })
              .onFetchDone(function(data, status) {
                  self._updateButtons("send", dialog, true);
              });

        this._super_(creme.dialog.Dialog, '_onOpen', dialog, frame, options);
    },

    _updateButtons: function(name, dialog, enabled)
    {
        var button = dialog ? $('.ui-dialog-buttonset button[name="' + name + '"]', dialog.parent()) : $([]);

        button.toggleClass('ui-state-disabled', !enabled);
        button.toggleAttr('disabled', !enabled);
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
