/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020  Hybird

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

var __DEFAULT_ERROR_MESSAGES = {
    badInput: null,
    patternMismatch: gettext("This value doesn't match the expected pattern ${pattern}"),
    rangeOverflow: gettext('This value must be inferior or equal to ${max}'),
    rangeUnderflow: gettext('This value must be superior or equal to ${min}'),
    stepMismatch: null,
    tooLong: gettext('Please remove some characters. This chain contains ${size} characters and only ${maxlength} are allowed'),
    tooShort: gettext('Please add some characters. This chain contains ${size} characters and at least ${minlength} are required'),
    typeMismatch: null,
    valueMissing: gettext("This value is required"),
    cleanMismatch: gettext('This value is not a valid "${dataType}"')
};

function __parseErrorMessages(element) {
    var messages = {};
    var entries = element.data();

    for (var attrName in entries) {
        if (attrName.match('^err[A-Z].+$')) {
            var errorKey = attrName.slice(3, 4).toLowerCase() + attrName.slice(4);
            messages[errorKey] = entries[attrName];
        }
    }

    return messages;
}

function __htmlErrorCode(validity) {
    if (validity && validity.valid === false) {
        for (var key in __DEFAULT_ERROR_MESSAGES) {
            if (validity[key] === true) {
                return key;
            }
        }
    }
}

function __htmlIsToggle(element) {
    return element.is('input[type="radio"], input[type="checkbox"]');
}

var __DEFAULT_DATA_TYPES = {
    radio: 'text',
    checkbox: 'text',
    hidden: 'text'
};

function __htmlDataType(element) {
    var htmlType = (element.attr('type') || 'text');
    return __DEFAULT_DATA_TYPES[htmlType] || htmlType;
}

creme.form = creme.form || {};

creme.form.Field = creme.component.Component.sub({
    _init_: function(element, options) {
        Assert.isAnyOf(element, ['string', $], 'DOM element "${e}" is not a string nor a jQuery element', {e: String(element)});

        element = $(element);
        Assert.that(element.size() === 1, 'A single DOM element is required');

        options = $.extend({
            initial: element.data('initial') || '',
            dataType: element.data('type') || __htmlDataType(element),
            preventBrowserTooltip: element.is('[data-notooltip]'),
            responsive: element.is('[data-responsive]')
        }, options || {});

        this._element = element;
        this._errorMessages = $.extend(
            {}, __DEFAULT_ERROR_MESSAGES,
            options.errorMessages || {},
            __parseErrorMessages(element)
        );

        this.preventBrowserTooltip(options.preventBrowserTooltip);

        this.readonly(options.readonly);
        this.required(options.required);
        this.disabled(options.disabled);
        this.multiple(options.multiple);
        this.checked(options.checked);
        this.initial(options.initial);
        this.dataType(options.dataType);
        this.responsive(options.responsive);
        this.formatter(options.formatter);
        this.parser(options.parser);

        element.on('invalid', this._onFieldInvalidHtml.bind(this));
        element.on('field-error', this._onFieldError.bind(this));
        element.on('propertychange keyup paste change input', this._onFieldChange.bind(this));

        // Fields can be "invalid" on document load, so we need update the messages on binding
        if (!this.isValidHtml()) {
            this.errorMessage(this._formatErrorMessage(this.htmlErrorCode()));
        }
    },

    trigger: function(event) {
        this._element.trigger('field-' + event, [this].concat(Array.copy(arguments).slice(1)));
    },

    readonly: function(readonly) {
        if (readonly === undefined) {
            return this._element.is('[readonly]');
        }

        if (this.readonly() !== readonly) {
            this._element.toggleAttr('readonly', readonly);
            this.trigger('prop-change', 'readonly', readonly);
        }

        return this;
    },

    disabled: function(disabled) {
        if (disabled === undefined) {
            return this._element.prop('disabled');
        }

        if (this.disabled() !== disabled) {
            this._element.prop('disabled', disabled);
            this.trigger('prop-change', 'disabled', disabled);
        }

        return this;
    },

    required: function(required) {
        if (required === undefined) {
            return this._element.prop('required');
        }

        if (this.required() !== required) {
            this._element.toggleAttr('required', required);
            this.trigger('prop-change', 'required', required);
        }

        return this;
    },

    multiple: function(multiple) {
        if (multiple === undefined) {
            return this._element.is('select[multiple]');
        }

        Assert.that(this._element.is('select'), 'This property can only be set on a select');

        if (this.multiple() !== multiple) {
            this._element.toggleAttr('multiple', multiple);
            this.trigger('prop-change', 'multiple', multiple);
        }

        return this;
    },

    checked: function(checked) {
        if (checked === undefined) {
            return this._element.prop('checked');
        }

        Assert.that(__htmlIsToggle(this._element), 'This property can only be set on a radio/checkbox input');

        if (this.checked() !== checked) {
            this._element.prop('checked', checked);
            this.trigger('prop-change', 'checked', checked);
        }

        return this;
    },

    responsive: function(state) {
        if (state === undefined) {
            return this._element.is('[data-responsive]') || this.form().is('[data-responsive]');
        }

        this._element.toggleAttr('data-responsive', state);
        return this;
    },

    dataType: function(dataType) {
        if (dataType === undefined) {
            return this._dataType ? this._dataType : __htmlDataType(this._element);
        }

        this._dataType = dataType;
        return this;
    },

    parser: function(parser) {
        if (parser === undefined) {
            return this._parser;
        }

        Assert.that(parser == null || Object.isFunc(parser), 'Field parser must be a me a function or null');

        this._parser = parser;
        return this;
    },

    formatter: function(formatter) {
        if (formatter === undefined) {
            return this._formatter;
        }

        Assert.that(formatter == null || Object.isFunc(formatter), 'Field formatter must be a me a function or null');

        this._formatter = formatter;
        return this;
    },

    form: function() {
        return this._element.parents('form:first');
    },

    preventBrowserTooltip: function(state) {
        if (state === undefined) {
            return this._element.is('[data-notooltip]') || this.form().is('[data-notooltip]');
        }

        this._element.toggleAttr('data-notooltip', state);
        return this;
    },

    initial: function(initial) {
        if (this.multiple() && Object.isString(initial)) {
            initial = initial.split(',');
        }

        return Object.property(this, '_initial', initial);
    },

    on: function() {
        this._element.on.apply(this._element, Array.copy(arguments));
    },

    off: function() {
        this._element.off.apply(this._element, Array.copy(arguments));
    },

    one: function() {
        this._element.one.apply(this._element, Array.copy(arguments));
    },

    element: function() {
        return this._element;
    },

    name: function() {
        return this._element.prop('name');
    },

    reset: function() {
        if (this.readonly()) {
            return this;
        }

        this.value(this._initial);
        this.trigger('reset', this._initial);
        return this;
    },

    htmlDataType: function() {
        return __htmlDataType(this._element);
    },

    isValid: function() {
        return Object.isEmpty(this.errorCode());
    },

    isValidHtml: function() {
        return this._element.get(0).validity.valid;
    },

    validateHtml: function() {
        var input = this._element.get(0);

        this.errorCode(null);
        var valid = input.checkValidity();

        this.error({
            code: this.htmlErrorCode()
        });

        return valid;
    },

    htmlErrorCode: function() {
        return __htmlErrorCode(this._element.get(0).validity);
    },

    errorMessage: function(message) {
        if (message === undefined) {
            return this._element.get(0).validationMessage || '';
        }

        this._element.get(0).setCustomValidity(message);
        return this;
    },

    errorCode: function(code) {
        if (code === undefined) {
            return this._errorCode || this.htmlErrorCode();
        }

        if (code === null) {
            this._errorCode = null;
            this.errorMessage('');
        } else {
            this._errorCode = code;
            this.errorMessage(this._formatErrorMessage(code));
        }

        return this;
    },

    error: function(error) {
        if (error === undefined) {
            return this.isValid() ? null : {
                code: this.errorCode(),
                message: this.errorMessage()
            };
        }

        if (error === null) {
            this._errorCode = null;
            this.errorMessage('');
        } else {
            this._errorCode = error.code;

            if (error.message) {
                this.errorMessage(error.message);
            } else {
                this.errorMessage(this._formatErrorMessage(error.code));
            }
        }

        this.trigger('error', this.isValid(), this.error());
        return this;
    },

    _onFieldInvalidHtml: function(e) {
        // Prevents default browser tooltip if enabled
        if (this.preventBrowserTooltip()) {
            e.preventDefault();
        }

        $(e.target).toggleClass('is-field-invalid', !this.isValid());
    },

    _onFieldError: function(e) {
        $(e.target).toggleClass('is-field-invalid', !this.isValid());
    },

    _onFieldChange: function(e) {
        if (this.responsive()) {
            this.clean({noThrow: true});
        }
    },

    _formatErrorMessage: function(code) {
        if (Object.isEmpty(code)) {
            return '';
        }

        var message = this._errorMessages[code];

        if (Object.isString(message)) {
            return message.template(this._errorMessageData.bind(this));
        } else {
            return this.errorMessage();
        }
    },

    _errorMessageData: function(name) {
        switch (name) {
            case 'dataType':
                return this.dataType();
            case 'name':
                return this.name();
            case 'value':
                return this.value();
            default:
                return this._element.attr(name);
        }
    },

    _formatValue: function(value) {
        var convertOpts = {from: this.dataType() || 'text', to: 'text'};
        var formatter = this._formatter;
        var hasFormatter = Object.isFunc(formatter);

        if (Object.isNone(value)) {
            return this.multiple() ? [] : null;
        }

        if (this.multiple()) {
            value = Array.isArray(value) ? value : [value];

            return value.map(function(item) {
                if (Object.isString(item)) {
                    return item;
                }

                return hasFormatter ? formatter(item, this) : creme.utils.convert(item, convertOpts);
            });
        } else {
            if (Object.isString(value)) {
                return value;
            }

            return hasFormatter ? formatter(value, this) : creme.utils.convert(value, convertOpts);
        }
    },

    _parseValue: function(value) {
        if (Object.isFunc(this._parser)) {
            return this._parser(value, this);
        } else {
            return creme.utils.convert(value, {
                from: 'text',
                to: this.dataType(),
                empty: !this.required()
            });
        }
    },

    value: function(value) {
        var previous = (!__htmlIsToggle(this._element) || this._element.prop('checked')) ? this._element.val() : null;

        if (value === undefined) {
            return previous;
        }

        if (this.readonly()) {
            return this;
        }

        var hasChanged = false;
        value = this._formatValue(value);

        if (this.multiple()) {
            hasChanged = (previous || []).join(',') !== (value || []).join(',');
        } else {
            hasChanged = previous !== value;
        }

        if (hasChanged) {
            this._element.val(value).change();
            this.trigger('change', this._element.val(), previous);
        }

        return this;
    },

    cleanValue: function(value) {
        try {
            return this._parseValue(value);
        } catch (e) {
            var error = new Error(this._formatErrorMessage('cleanMismatch'));
            error.code = 'cleanMismatch';
            throw error;
        }
    },

    clean: function(options) {
        options = options || {};

        var value = this.value();
        var cleaned, error;

        try {
            if (this.validateHtml()) {
                try {
                    cleaned = this.cleanValue(value);
                } catch (e) {
                    this.error({
                        code: e.code,
                        message: e.message
                    });

                    error = e;
                }
            } else {
                error = new Error(this.errorMessage());
                error.code = this.errorCode();
            }
        } finally {
            this.trigger('clean', cleaned, value);
        }

        if (error && !options.noThrow) {
            throw error;
        }

        return cleaned;
    }
});

creme.utils.newJQueryPlugin({
    name: 'flyfield',
    create: function(options) {
        return new creme.form.Field($(this), options);
    },
    methods: [
        'clean', 'value', 'reset', 'validateHtml'
    ],
    properties: [
        'disabled', 'readonly', 'multiple', 'checked', 'name',
        'dataType', 'htmlDataType', 'responsive', 'initial', 'preventBrowserTooltip',
        'errorCode', 'errorMessage', 'isValid', 'isValidHtml'
    ]
});

}(jQuery));
