/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

/* globals creme_media_url */
(function($) {
"use strict";

creme.forms = {};

/*
 * TimePicker widget
 */
creme.forms.TimePicker = {};
creme.forms.TimePicker.init = function(self) {
    var time = creme.forms.TimePicker.timeval(self);
    var disabled = $('input[type="hidden"]', self).is('[disabled]');

    $('li.hour input[type="number"]', self).val(time.hour);
    $('li.minute input[type="number"]', self).val(time.minute);

    if (disabled) {
        $('li input[type="number"]', self).prop('disabled', true);
        $('li button', self).prop('disabled', true);
    } else {
        $('li input[type="number"]', self).on('change', function() {
                creme.forms.TimePicker.update(self);
        });
        $('li button', self).on('click', function() {
            var now = new Date();
            creme.forms.TimePicker.set(self, now.getHours(), now.getMinutes());
        });
    }
};

creme.forms.TimePicker.parseTime = function(value) {
    var values = (value !== undefined) ? value.split(':') : [];
    var hour = (values.length > 1) ? values[0] : '';
    var minute = (values.length > 1) ? values[1] : '';

    return {
        hour: hour,
        minute: minute
    };
};

creme.forms.TimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
};

creme.forms.TimePicker.timeval = function(self) {
    return creme.forms.TimePicker.parseTime($('input[type="hidden"]', self).val());
};

creme.forms.TimePicker.update = function(self) {
    var hour = $('li.hour input[type="number"]', self).val();
    var minute = $('li.minute input[type="number"]', self).val();
    $('input[type="hidden"]', self).val(hour + ':' + minute);
};

creme.forms.TimePicker.clear = function(self) {
    $('li.hour input[type="number"]', self).val('');
    $('li.minute input[type="number"]', self).val('');
    $('input[type="hidden"]', self).val('');
};

creme.forms.TimePicker.set = function(self, hour, minute) {
    $('li.hour input[type="number"]', self).val(hour);
    $('li.minute input[type="number"]', self).val(minute);
    $('input[type="hidden"]', self).val(hour + ':' + minute);
};

/*
 * DateTimePicker widget
 */
creme.forms.DateTimePicker = {};
creme.forms.DateTimePicker.init = function(self, format) {
    format = format || 'yy-mm-dd';

    var datetime = creme.forms.DateTimePicker.datetimeval(self);

    $('li.date input[type="text"]', self).val(datetime.date);
    $('li.hour input[type="number"]', self).val(datetime.hour);
    $('li.minute input[type="number"]', self).val(datetime.minute);

    $('li input:not([type="hidden"])', self).on('change propertychange keyup input paste', function() {
        creme.forms.DateTimePicker.update(self);
    });

    $('li.now button', self).on('click', function(e) {
            e.preventDefault();
            creme.forms.DateTimePicker.setDate(self, new Date());
        });

    $('li.clear button', self).on('click', function(e) {
            e.preventDefault();
            creme.forms.DateTimePicker.clear(self);
        });

    $('li.date input[type="text"]', self).datepicker({
            dateFormat:      format,
            showOn:          "button",
            buttonText:      gettext("Calendar"),
            buttonImage:     creme_media_url("images/icon_calendar.gif"),
            buttonImageOnly: true
        });
};

creme.forms.DateTimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
};

creme.forms.DateTimePicker.datetimeval = function(self) {
    return creme.forms.DateTimePicker.parseDateTime($('input[type="hidden"]', self).val());
};

creme.forms.DateTimePicker.parseDateTime = function(value) {
    var values = (value !== undefined) ? value.split(' ') : [];
    var date = (values.length > 1) ? values[0] : '';
    var time = creme.forms.TimePicker.parseTime((values.length > 1) ? values[1] : '');
    return $.extend({date: date}, time);
};

creme.forms.DateTimePicker.update = function(self) {
    var date = $('li.date input[type="text"]', self).val();
    var hour = $('li.hour input[type="number"]', self).val();
    var minute = $('li.minute input[type="number"]', self).val();
    $('input[type="hidden"]', self).val(date + ' ' + hour + ':' + minute);
};

creme.forms.DateTimePicker.clear = function(self) {
    $('li.date input[type="text"]', self).val('');
    $('li.hour input[type="number"]', self).val('');
    $('li.minute input[type="number"]', self).val('');
    $('input[type="hidden"]', self).val('');
};

creme.forms.DateTimePicker.setDate = function(self, date) {
    var hour = date.getHours();
    var minute = date.getMinutes();

    $('li.date input[type="text"]', self).datepicker('setDate', date);
    $('li.hour input[type="number"]', self).val(hour);
    $('li.minute input[type="number"]', self).val(minute);

    creme.forms.DateTimePicker.update(self);
};

creme.forms.DateTimePicker.set = function(self, year, month, day, hour, minute) {
    creme.forms.DateTimePicker.setDate(self, new Date(year, month, day, hour, minute));
};

// Backport from jquery.form-3.51
// TODO : factorize code in form controller
function __validateHTML5(element) {
    var errors = {};

    $('*:invalid', element).each(function(index, item) {
        errors[$(this).prop('name')] = item.validationMessage;
    });

    return errors;
}

// TODO : create a real form controller with better lifecycle (not just a css class) and
//        factorize some code with creme.dialog.FormDialog for html5 validation.
creme.forms.initialize = function(form) {
    if (form.is(':not(.is-form-active)')) {
        form.addClass('is-form-active');

        // HACK : By default the browser aligns the page to the top position of the invalid HTML5 field.
        //        and it will be hidden by the fixed header menu.
        //        This listener will force browser to scroll from the BOTTOM (false argument) and "solve" the problem.
        $('input,select,textarea', form).on('invalid', function(e) {
            this.scrollIntoView(false);
            $(e.target).addClass('is-field-invalid');
        });

        // HACK : Prevent multiple submit and also preserve <button type="submit" value="..."/> behaviour in wizards.
        form.on('click', '[type="submit"]', function(e) {
            var button = $(this);

            // A submit input/button can force deactivation of html5 validation.
            if (button.is('[data-no-validate]')) {
                form.attr('novalidate', 'novalidate');
            }

            var isHtml5Valid = Object.isEmpty(__validateHTML5(form));

            if (isHtml5Valid === true) {
                if (button.is(':not(.is-form-submit)')) {
                    button.addClass('is-form-submit');
                } else {
                    e.preventDefault();
                }
            }
        }).on('submit', function() {
            form.find('[type="submit"]').addClass('is-form-submit');
        });

        creme.utils.scrollTo($('.errorlist:first, .non_field_errors', form));
    }
};


creme.forms.validateHtml5Field = function(field, options) {
    options = options || {};
    var errors = {};

    if (options.noValidate || field.is('[novalidate]')) {
        return errors;
    }

    if (field.is(':invalid')) {
        var message = field.get(0).validationMessage || '';

        errors[$(field).prop('name')] = message;

        field.addClass('is-field-invalid');
        field.trigger('html5-invalid', [true, message]);
    } else {
        field.removeClass('is-field-invalid');
        field.trigger('html5-invalid', [false]);
    }

    return errors;
};

creme.forms.validateHtml5Form = function(form, options) {
    options = options || {};
    var errors = {};
    var fieldOptions = {
         noValidate: options.noValidate || form.is('[novalidate]')
    };

    var inputs = $('input, select, textarea, datalist, output', form);

    inputs.filter(':not([type="submit"])').trigger('html5-pre-validate', [options]);
    inputs.each(function() {
        $.extend(errors, creme.forms.validateHtml5Field($(this), fieldOptions));
    });

    return errors;
};
}(jQuery));
