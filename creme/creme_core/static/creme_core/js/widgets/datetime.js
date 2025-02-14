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

/* TODO: factorise? */
creme.widget.YearPicker = creme.widget.declare('ui-creme-yearpicker', {
    options: {
        readonly: false,
        disabled: false
    },

    _create: function(element, options, cb, sync) {
        this._input = element;
        this._disabled = creme.object.isTrue(options.disabled) && element.prop('disabled');
        this._readonly = creme.object.isTrue(options.readonly) && element.prop('readonly');

        element.prop('disabled', this._disabled);
        element.prop('readonly', this._readonly);

        var parent = element.parent();

        var list = $('<ul/>').addClass('ui-layout hbox').append($('<li/>').append(element));
        parent.append(list);

        this._buttons = this._initHelperButtons();
        this._buttons.forEach(function(button) {
            list.append($('<li/>').append(button));
        });

        this._updateDisabledState(element, this._disabled);

        element.addClass('widget-ready');
    },

    _updateDisabledState: function(element, disabled) {
        var state = disabled || this._readonly;

        this._buttons.forEach(function(button) {
            button.prop('disabled', state);
        });
    },

    _initHelperButtons: function() {
        var input = this._input;
        var button = $('<button>').attr('name', 'current-year')
                                  .attr('type', 'button')
                                  .html(gettext('Current year'));

        button.on('click', function(e) {
            e.preventDefault();
            input.val(new Date().getFullYear());
        });

        return [button];
    },

    val: function(element, value) {
        if (value === undefined) {
            return element.val();
        }

        element.val(value);
        return this;
    }
});

creme.widget.DatePicker = creme.widget.declare('ui-creme-datepicker', {
    options: {
        /* Know issue: it seems our JS component removes "0" padding for initial value with years < 1000 in the input (but accepts 0 padded years) */
        format: 'dd-mm-yy',
        readonly: false,
        disabled: false
    },

    _create: function(element, options, cb, sync) {
        this._disabled = creme.object.isTrue(options.disabled) && element.prop('disabled');
        this._readonly = creme.object.isTrue(options.readonly) && element.prop('readonly');

        element.prop('disabled', this._disabled);
        element.prop('readonly', this._readonly);

        var parent = element.parent();

        var list = $('<ul/>').addClass('ui-layout hbox').append($('<li/>').append(element));

        parent.append(list);

        this._datepicker = element.datepicker({dateFormat: options.format,
                                               showOn: "button",
                                               buttonText: gettext('Calendar'),
                                               buttonImage: creme_media_url('images/icon_calendar.gif'),
                                               buttonImageOnly: true });

        list.append($('<li/>').append($('<span/>').addClass('ui-creme-datepicker-trigger')
                                                  .append($('img.ui-datepicker-trigger', parent))));

        this._buttons = this._initHelperButtons();
        this._buttons.forEach(function(button) {
            list.append($('<li/>').append(button));
        });

        this._updateDisabledState(element, this._disabled);

        element.addClass('widget-ready');
    },

    _updateDisabledState: function(element, disabled) {
        var state = disabled || this._readonly;
        this._datepicker.datepicker('option', 'disabled', state);
        this._buttons.forEach(function(button) {
            button.prop('disabled', state);
        });
    },

    _appendHelperButton: function(buttons, name, label, getter) {
        var datepicker = this._datepicker;
        var button = $('<button>').attr('name', name)
                                  .attr('type', 'button')
                                  .html(gettext(label));

        button.on('click', function(e) {
            e.preventDefault();
            datepicker.datepicker('setDate', getter(datepicker.datepicker('getDate')));
        });

        buttons.push(button);
        return button;
    },

    _initHelperButtons: function() {
        var buttons = [];
        this._appendHelperButton(buttons, 'today', 'Today', function(current) { return new Date(); });
        return buttons;
    },

    val: function(element, value) {
        if (value === undefined) {
            return element.val();
        }

        element.val(value);
        return this;
    }
});


creme.widget.DateTimePicker = creme.widget.declare('ui-creme-datetimepicker', {
    options: {
        format: 'dd-mm-yy',
        readonly: false,
        disabled: false
    },

    _create: function(element, options, cb, sync) {
        var input = $('input[type="hidden"]', element);

        this._disabled = creme.object.isTrue(options.disabled) || input.prop('disabled');
        this._readonly = creme.object.isTrue(options.readonly) || input.prop('readonly');

        element.toggleClass('is-readonly', this._readonly);

        input.prop('disabled', this._disabled);
        input.prop('readonly', this._readonly);

        creme.forms.DateTimePicker.init(element, options.format);

        input.on('change', function() {
            var datetime = creme.forms.DateTimePicker.parseDateTime($(this).val());

            $('li.date input[type="text"]', element).val(datetime.date);
            $('li.hour input[type="number"]', element).val(datetime.hour);
            $('li.minute input[type="number"]', element).val(datetime.minute);
        });

        this._datepicker = $('li.date input[type="text"]', element).datepicker();
        this._buttons = $('button[type="button"]', element);

        this._updateDisabledState(element, this._disabled);
        element.addClass('widget-ready');
    },

    _updateDisabledState: function(element, disabled) {
        var state = disabled || this._readonly;
        this._datepicker.datepicker('option', 'disabled', state);
        this._buttons.prop('disabled', state);
        $('li input[type="text"],li input[type="number"]', element).prop('disabled', state);
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.forms.DateTimePicker.val(element);
        }

        $('input[type="hidden"]', element).val(value).trigger('change');
        return this;
    }
});

}(jQuery));
