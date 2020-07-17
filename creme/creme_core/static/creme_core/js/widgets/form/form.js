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

creme.form = creme.form || {};

var __ident = function(value) {
    return value;
};

var __addRawEntry = function(data, key, value) {
    if (!Object.isEmpty(key) && !Object.isNone(value)) {
        var stored = data[key];

        if (stored === undefined) {
            data[key] = value;
        } else {
            stored = Array.isArray(stored) ? stored : [stored];
            value = Array.isArray(value) ? value : [value];
            data[key] = stored.concat(value);
        }
    }
};

creme.form.Form = creme.component.Component.sub({
    _init_: function(element, options) {
        Assert.isAnyOf(element, ['string', $], 'DOM element "${e}" is not a string nor a jQuery element', {e: String(element)});

        element = $(element);
        Assert.that(element.size() === 1, 'A single DOM element is required');

        options = $.extend({
            validator: __ident,

            fieldSelector: 'input:not([type="submit"]), select, textarea',
            errorListSelector: '.errorlist',
            submitSelector: '[type="submit"]',

            scrollOnError: false,
            noValidate: element.is('[novalidate]'),
            preventBrowserTooltip: element.is('[data-notooltip]'),
            responsive: element.is('[data-responsive]')
        }, options || {});

        this._element = element;
        this._errorMessages = options.errorMessages || {};

        this.validator(options.validator);

        this.fieldSelector(options.fieldSelector);
        this.submitSelector(options.submitSelector);
        this.errorListSelector(options.errorListSelector);

        this.scrollOnError(options.scrollOnError);
        this.noValidate(options.noValidate);
        this.preventBrowserTooltip(options.preventBrowserTooltip);
        this.responsive(options.responsive);

        element.on('click', this._submitSelector, this._onButtonSubmit.bind(this));
        element.on('submit', this._onFormSubmit.bind(this));
    },

    trigger: function(event) {
        this._element.trigger('form-' + event, [this].concat(Array.copy(arguments).slice(1)));
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

    validator: function(validator) {
        Assert.that(Object.isNone(validator) || Object.isFunc(validator),
                    'Validator must be a function');

        return Object.property(this, '_validator', validator);
    },

    errorListSelector: function(selector) {
        return Object.property(this, '_errorListSelector', selector);
    },

    submitSelector: function(selector) {
        return Object.property(this, '_submitSelector', selector);
    },

    fieldSelector: function(selector) {
        return Object.property(this, '_fieldSelector', selector);
    },

    preventBrowserTooltip: function(status) {
        var form = this._element;

        if (status === undefined) {
            return form.is('[data-notooltip]');
        }

        form.toggleAttr('data-notooltip', status);
        return this;
    },

    responsive: function(status) {
        var form = this._element;

        if (status === undefined) {
            return form.is('[data-responsive]');
        }

        form.toggleAttr('data-responsive', status);
        return this;
    },

    noValidate: function(status) {
        var form = this._element;

        if (status === undefined) {
            return form.is('[novalidate]');
        }

        form.toggleAttr('novalidate', status);
        return this;
    },

    scrollOnError: function(status) {
        return Object.property(this, '_scrollOnError', status);
    },

    element: function() {
        return this._element;
    },

    selectSubmits: function() {
        return this._element.find(this._submitSelector);
    },

    selectFields: function() {
        return this._element.find(this._fieldSelector);
    },

    isValid: function() {
        if (this.noValidate()) {
            return true;
        }

        return this.isValidHtml() && this.clean({noThrow: true}).isValid;
    },

    isValidHtml: function() {
        if (this.noValidate()) {
            return true;
        }

        return this.fields().every(function(field) {
            return field.isValidHtml();
        });
    },

    validateHtml: function() {
        if (this.noValidate()) {
            return true;
        }

        var valid = this.fields().every(function(field) {
            return field.validateHtml();
        });

        this.trigger('validate', valid, this.errors());
        return valid;
    },

    reset: function() {
        this.fields().forEach(function(field) {
            field.reset();
        });
    },

    initialData: function(data) {
        if (data !== undefined) {
            this.fields().forEach(function(field) {
                field.initial(data[field.name()]);
            });

            return this;
        }

        var output = {};

        this.fields().forEach(function(field) {
            if (field.name()) {
                __addRawEntry(output, field.name(), field.initial());
            }
        });

        return output;
    },

    data: function(data) {
        if (data !== undefined) {
            this.fields().forEach(function(field) {
                field.value(data[field.name()]);
            });

            return this;
        }

        var output = {};

        this._element.serializeArray().forEach(function(e) {
            __addRawEntry(output, e.name, e.value);
        });

        return output;
    },

    clean: function(options) {
        options = options || {};

        var data = this.data();
        var cleanedData = {};
        var isValid = true;
        var noValidate = this.noValidate();
        var fields = this.fields();

        fields.forEach(function(field) {
            var name = field.name();

            try {
                cleanedData[name] = field.clean();
            } catch (e) {
                isValid = noValidate;
            }
        });

        var output = {
            data: data,
            cleanedData: cleanedData,
            isValid: isValid,
            fieldErrors: this.errors()
        };

        if (isValid) {
            output = this._cleanFormData(output);

            fields.forEach(function(field) {
                var error = output.fieldErrors[field.name()];

                if (error && error.code) {
                    field.error(error);
                }
            });

            isValid = output.isValid = (Object.isEmpty(output.fieldErrors) && Object.isEmpty(output.errors)) || noValidate;
        }

        this.trigger('clean', output);

        if (output.isValid || options.noThrow) {
            return output;
        } else {
            var error = new Error('Form data is invalid');
            error.output = output;
            throw error;
        }
    },

    _cleanFormData: function(data) {
        var output = {};

        try {
            output = this._validator.bind(this)(data);
        } catch (e) {
            output.errors = [e.message];
        }

        return $.extend({}, data, output);
    },

    errors: function(errors) {
        if (errors !== undefined) {
            this.fields().forEach(function(field) {
                var error = errors[field.name()];

                if (error) {
                    field.error(error);
                }
            });

            return this;
        }

        var output = {};

        if (this.noValidate() === false) {
            this.fields().forEach(function(field) {
                if (!field.isValid()) {
                    __addRawEntry(output, field.name(), {
                        code: field.errorCode(),
                        message: field.errorMessage()
                    });
                }
            });
        }

        return output;
    },

    _boundField: function(field) {
        var bound = field.flyfield('instance');

        if (Object.isNone(bound)) {
            bound = field.flyfield({
                errorMessages: this._errorMessages
            });
        }

        return bound;
    },

    url: function() {
        return this._element.attr('action') || '';
    },

    fields: function() {
        var _boundField = this._boundField.bind(this);

        return this.selectFields().filter('[name]:not([name=""])').map(function() {
            return _boundField($(this));
        }).get();
    },

    field: function(name) {
        Assert.not(Object.isEmpty(name), 'Field name cannot be empty');

        var _boundField = this._boundField.bind(this);

        return this.selectFields().filter('[name="' + name + '"]').map(function() {
            return _boundField($(this));
        }).get(0);
    },

    submit: function(listeners) {
        this.one(listeners);
        this._element.submit();
        return this;
    },

    ajaxSubmit: function(data, options) {
        return this.ajaxQuery(data, options).post();
    },

    ajaxQuery: function(data, options) {
        options = $.extend({
            url: this.url()
        }, options || {});

        var self = this;
        var query = new creme.ajax.Query(options);

        query.url(options.url)
             .data(function() {
                  return $.extend({}, data || {}, self.clean().cleanedData);
              });

        query.on('start', function() {
                  self.toggleSubmitState(true);
              }).onComplete(function() {
                  self.toggleSubmitState(false);
              });

        return query;
    },

    isSubmitting: function() {
        return this.element().is('.is-form-submit');
    },

    scrollToInvalidField: function() {
        var field = this._element.find(this._fieldSelector).filter(':invalid').first();

        // HACK : By default the browser aligns the page to the top position of the invalid HTML5 field.
        //        and it will be hidden by the fixed header menu.
        //        This listener will force browser to scroll from the BOTTOM (false argument) and "solve" the problem.
        if (field.size() > 0) {
            field.get(0).scrollIntoView(false);
        }
    },

    scrollToErrorList: function() {
        var list = this._element.find(this._errorListSelector);
        creme.utils.scrollTo(list);
    },

    toggleSubmitState: function(state) {
        this.element().toggleClass('is-form-submit', state);
        this.selectSubmits().toggleClass('is-form-submit', state);
    },

    _onButtonSubmit: function(e) {
        var button = $(e.target);

        // A submit input/button can force deactivation of html5 validation.
        if (button.is('[data-novalidate]')) {
            this.noValidate(true);
        }

        // HACK : Prevent multiple submit and also preserve <button type="submit" value="..."/> behaviour in wizards.
        if (button.is('.is-form-submit')) {
            e.preventDefault();
        } else {
            this._onFormSubmit(e);
        }
    },

    _onFormSubmit: function(e) {
        if (this.isSubmitting()) {
            e.preventDefault();
        } else {
            var output = this.clean({noThrow: true});

            if (output.isValid) {
                this.toggleSubmitState(true);
                this.trigger('submit', output);
            } else if (this.scrollOnError()) {
                this.scrollToInvalidField();
            }
        }
    }
});

creme.utils.newJQueryPlugin({
    name: 'flyform',
    create: function(options) {
        return new creme.form.Form($(this), options);
    },
    methods: [
        'clean', 'submit', 'reset', 'validateHtml'
    ],
    properties: [
        'url', 'responsive', 'initialData', 'data', 'preventBrowserTooltip',
        'validator', 'isValid', 'isValidHtml', 'isSubmitting'
    ]
});

}(jQuery));
