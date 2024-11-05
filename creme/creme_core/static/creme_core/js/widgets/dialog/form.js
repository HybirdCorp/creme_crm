/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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

/*
 * Requires : creme.utils
 */

(function($) {
"use strict";

creme.dialog = creme.dialog || {};

var _defaultValidator = function(response, dataType) {
    return !response.isHTML() || response.content.match(/<form[^>]*>/) === null;
};

var _innerPopupValidator = function(response, dataType) {
    console.warn('"innerpopup" validator of creme.dialog.FormDialog is now deprecated; should use "default" instead');

    var content = response.content;

    if (Object.isEmpty(content) || !response.isHTML()) {
        return true;
    }

    if (content.match(/^<div[^>]+class="in-popup"[^>]*>/)) {
        if (content.match(/^<div[^>]+closing="true"[^>]*>/)) {
            return true;
        }

        return (content.match(/<form[^>]*>/) === null);
    }

    return false;
};

var _FORM_VALIDATORS = {
    'default': _defaultValidator,
    'innerpopup': _innerPopupValidator
};

creme.dialog.FormDialog = creme.dialog.Dialog.sub({
    _init_: function(options) {
        options = $.extend({
            autoFocus: true,
            submitOnKey: 13,
            submitData: {},
            noValidate: false,
            validator: 'default',
            closeOnFormSuccess: true
        }, options || {});

        this._super_(creme.dialog.Dialog, '_init_', options);
        this.validator(options.validator);

        this.frame().on('before-submit before-fetch', this._onBeforeFrameUpdate.bind(this));

        this._submitListeners = {
            'submit-done': this._onSubmitDone.bind(this),
            'submit-fail': this._onSubmitFail.bind(this)
        };

        this._submitKeyCb = this._onSubmitKey.bind(this);
        this._submitKey = options.submitOnKey ? options.submitOnKey : false;
    },

    validator: function(validator) {
        if (validator === undefined) {
            return this._validator;
        }

        var cleaned = Object.isString(validator) ? _FORM_VALIDATORS[validator] : validator;

        if (!Object.isFunc(cleaned)) {
            if (Object.isString(validator)) {
                throw new Error('FormDialog validator "${validator}" is unknown'.template({validator: validator}));
            } else {
                throw new Error('FormDialog validator "${validator}" is not a function'.template({validator: validator}));
            }
        }

        this._validator = cleaned.bind(this);
        return this;
    },

    _validate: function(data, dataType) {
        var validator = this.validator();
        return !Object.isFunc(validator) || validator(data, dataType);
    },

    _frameSubmitData: function(data) {
        var options = this.options;
        var submitData = Object.isFunc(options.submitData) ? options.submitData.bind(this)(options, data) : options.submitData || {};
        return $.extend({}, submitData, data);
    },

    form: function() {
        return $('form:first', this.content());
    },

    submit: function(options, data, listeners) {
        options = options || {};

        var form = this.form();
        var errors = creme.forms.validateHtml5Form(form, {
            noValidate: options.noValidate || this.options.noValidate
        });

        if (Object.isEmpty(errors) === false) {
            return this;
        }

        data = Object.isFunc(data) ? data.bind(this)(options) : data;
        var submitData = this._frameSubmitData(data);

        this.frame().submit('', $.extend({}, options, {data: submitData}), form, this._submitListeners);
        return this;
    },

    _onBeforeFrameUpdate: function() {
        this._updateButtonState("send", false);
        this._updateButtonState("cancel", true, false);
    },

    _onFrameCleanup: function() {
        this._super_(creme.dialog.Dialog, '_onFrameCleanup');
        this.frame().delegate().off('keypress', this._submitKeyCb);
    },

    _onFrameUpdate: function(event, data, dataType, action) {
        if (action !== 'submit') {
            this._super_(creme.dialog.Dialog, '_onFrameUpdate', event, data, dataType, action);
        }

        var content = this.frame().delegate();

        if (this.options.autoFocus) {
            var autofocus = $('[autofocus]:tabbable:first', content);

            if (autofocus.length > 0) {
                autofocus.trigger('focus');
            } else {
                $(':tabbable:first', content).trigger('focus');
            }
        } else {
            $(':tabbable', content).trigger('blur');
        }

        content.on('keypress', this._submitKeyCb);
    },

    _onSubmitDone: function(event, response, dataType) {
        if (this._validate(response, dataType)) {
            this.trigger('form-success', response, dataType);

            /*
             * TODO : This is a hotfix for 2.3 release without changing the
             * behaviour of the DialogForm : actually the "close" event is
             * considered as the cancellation of the form so we can't send it
             * along with a "form-success".
             *
             * In the next release we will use self.close() and send the "close"
             * event after ALL valid submits and send a "cancel" event when the
             * cancel/close button is pressed.
             */
            if (this.options.closeOnFormSuccess) {
                this._frame.clear();
                this._destroyDialog();
            } else {
                this._removeButton('send');
                // TODO : Remove this hack once the 'cancel' behavior will be distinct
                // from 'close' (see the previous TODO).
                this._updateButtonLabel('cancel', gettext('Close'));
            }
        } else {
            this._super_(creme.dialog.Dialog, '_onFrameUpdate', event, response.content, dataType, 'submit');
            this._updateButtonState("send", true, 'auto');
            this._updateButtonState("cancel", true);

            this.trigger('form-error', response.content, dataType);
        }
    },

    _onSubmitFail: function(event, data, statusText) {
        this._updateButtonState("send", false);
        this._updateButtonState("cancel", true, true);
    },

    _onSubmitKey: function(e) {
        if (e.keyCode === this._submitKey && $(e.target).is(':not(textarea)')) {
            e.preventDefault();
            this.button('send').trigger('click');
        }
    },

    _onOpen: function(dialog, frame, options) {
        var self = this;

        frame.onFetchFail(function(data, status) {
                  self._updateButtonState("send", false);
                  self._updateButtonState("cancel", true, true);
              })
              .onFetchDone(function(data, status) {
                  self._updateButtonState("send", true, 'auto');
                  self._updateButtonState("cancel", true);
              });

        this._super_(creme.dialog.Dialog, '_onOpen', dialog, frame, options);
    },

    _frameActionFormSubmitButtons: function(options) {
        var self = this;
        var buttons = {};
        var buttonIds = {};
        var submitCb = function(button, e, options) {
            options = $.extend({
                noValidate: button.is('[novalidate]')
            }, options || {});

            this.submit(options, options.data);
        };
        var buildUniqueButtonId = function(id) {
            var suffix = buttonIds[id] || 0;
            buttonIds[id] = suffix + 1;

            return (suffix > 0) ? id + '-' + suffix : id;
        };

        $('.ui-creme-dialog-action[type="submit"]', this.content()).each(function() {
            var item  = $(this);
            var data  = {};
            var name  = item.attr('name');
            var label = item.text();
            var order = parseInt(item.attr('data-dialog-action-order') || 0);
            var value = item.val();
            var id = buildUniqueButtonId(name || 'send');
            var noValidate = item.is('[data-no-validate]');

            if (item.is('input')) {
                label = value || gettext('Save');
            } else {
                label = label || gettext('Save');

                if (!Object.isEmpty(name) && !Object.isNone(value)) {
                    data[name] = value;
                }
            }

            self._appendButton(buttons, id, label, submitCb,
                               {data: data, order: order, noValidate: noValidate});
        }).toggleProp('disabled', true);

        if (Object.isEmpty(buttons)) {
            this._appendButton(buttons, 'send', gettext('Save'), submitCb);
        }

        return buttons;
    },

    _frameActionButtons: function(options) {
        var buttons = this._super_(creme.dialog.Dialog, '_frameActionButtons', options);
        $.extend(buttons, this._frameActionFormSubmitButtons(options));
        return buttons;
    },

    _defaultButtons: function(buttons, options) {
        this._appendButton(buttons, 'cancel', gettext('Cancel'), function(button, e, options) {
                               this.close();
                           });

        return buttons;
    },

    onFormSuccess: function(listeners) {
        this._events.bind('form-success', listeners);
        return this;
    },

    onFormError: function(listeners) {
        this._events.bind('form-error', listeners);
        return this;
    },

    submitKey: function(value) {
        return Object.property(this, '_submitKey', value);
    }
});

creme.dialog.FormDialogAction = creme.component.Action.sub({
    _init_: function(options, listeners) {
        this._super_(creme.component.Action, '_init_', this._openPopup, options);
        this._listeners = listeners || {};
    },

    _onSubmit: function(event, response, dataType) {
        this.done(response, dataType);
    },

    _buildPopup: function(options) {
        var self = this;
        options = $.extend({}, this.options(), options || {});

        var form = new creme.dialog.FormDialog(options).onFormSuccess(this._onSubmit.bind(this))
                                                       .onClose(function() {
                                                           self.cancel();
                                                       })
                                                       .on(this._listeners);

        return form;
    },

    _openPopup: function(options) {
        this._buildPopup(options).open();
    }
});
}(jQuery));
