/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021  Hybird

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

var __STATE_FIELDNAMES = ['TOTAL_FORMS', 'INITIAL_FORMS', 'MAX_NUM_FORMS'];

creme.form.FormSet = creme.form.Form.sub({
    _init_: function(element, options) {
        options = $.extend({
            formSelector: 'data-formset-form',
            formPrefixFormat: '${prefix}form-${index}-'
        }, options || {});

        this._formOptions = options.form || {};
        console.trace(element, options);
        this._super_(creme.form.Form, '_init_', element, options);

        this.formSelector(options.formSelector);
        this.formPrefixFormat(options.formPrefixFormat);
    },

    formPrefixFormat: function(format) {
        return Object.property(this, '_formPrefixFormat', format);
    },

    formSelector: function(selector) {
        return Object.property(this, '_formSelector', selector);
    },

    selectForms: function() {
        return this._element.find(this.formSelector());
    },

    _boundForm: function(form) {
        var bound = form.flyform('instance');

        if (Object.isNone(bound)) {
            bound = form.flyform(this._formOptions || {});
        }

        return bound;
    },

    forms: function() {
        var _boundForm = this._boundForm.bind(this);
        var prefixFormat = this.formPrefixFormat();
        var formsetPrefix = this.prefix();

        return this.selectForms().map(function(index) {
            var prefix = prefixFormat.template({prefix: formsetPrefix, index: index});
            return _boundForm($(this)).prefix(prefix);
        }).get();
    },

    form: function(index) {
        Assert.not(Object.isEmpty(index), 'Form index cannot be empty');
        var prefix = this.prefixFormat().template({index: index});

        var matches = this.forms().filter(function(form) {
            return form.prefix() === prefix;
        });

        return matches ? matches[0] : undefined;
    },

    clean: function(options) {
        options = options || {};

        var formOutputs = this.forms().map(function(form) {
            return form.clean({
                noThrow: true,
                stopPropagation: true
            });
        });

        var output = {
            prefix: this.prefix(),
            data: {},
            cleanedData: {},
            isValid: true,
            errors: [],
            fieldErrors: {}
        };

        formOutputs.forEach(function(formOutput) {
            output.isValid |= formOutput.isValid;

            $.extend(output.data, formOutput.data);
            $.extend(output.cleanedData, formOutput.cleanedData);
            $.extend(output.fieldErrors, formOutput.fieldErrors);
        });

        $.extend(output.cleanedData, this.stateData());

        if (output.isValid) {
            output = this._applyConstraints(output, options);
        }

        if (options.stopPropagation) {
            this.trigger('clean', output);
        }

        if (output.isValid || options.noThrow) {
            return output;
        } else {
            throw new creme.form.ValidationError({
                message: 'Formset data is invalid',
                output: output
            });
        }
    },

    reset: function() {
        this.forms().forEach(function(form) {
            form.reset();
        });

        return this;
    },

    stateFields: function() {
        var stateField = this.stateField.bind(this);

        return __STATE_FIELDNAMES.map(function(name) {
            return stateField(name);
        }).filter(function(field) {
            return field !== undefined;
        });
    },

    stateField: function(name) {
        Assert.in(name, __STATE_FIELDNAMES, '"${value}" is not a valid formset status field');
        return this.field(this.prefix() + name);
    },

    stateData: function(data) {
        if (data !== undefined) {
            for (var name in data) {
                this.stateField(name).value(data);
            }
        }

        var output = {};
        var prefix = this.prefix();
        var stateField = this.stateField.bind(this);

        __STATE_FIELDNAMES.forEach(function(name) {
            var field = stateField(name);
            output[prefix + name] = field ? field.clean({noThrow: true}) || 0 : 0;
        });

        return output;
    },

    addForm: function(element) {
        return this;
    },

    removeForm: function(index) {
        return this;
    }
});

creme.utils.newJQueryPlugin({
    name: 'flyformset',
    create: function(options) {
        return new creme.form.FormSet($(this), options);
    },
    methods: [
        'clean', 'submit', 'reset', 'validateHtml'
    ],
    properties: [
        'url', 'prefix', 'constraints',
        'responsive', 'noValidate', 'preventBrowserTooltip', 'scrollOnError',
        'initialData', 'data', 'errors', 'stateData',
        'fields', 'forms', 'stateFields',
        'isValid', 'isValidHtml', 'isSubmitting'
    ]
});

}(jQuery));
