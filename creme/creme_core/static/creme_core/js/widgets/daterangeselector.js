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

/* globals creme_media_url */
(function($) {
"use strict";

/*
 * TODO : Merge with DateRange ???
 */
creme.widget.DateRangeSelector = creme.widget.declare('ui-creme-daterange-selector', {
    options: {
        cloneDatePickers: true
    },

    _create: function(element, options, cb, sync) {
        options = Object.assign({
            format: element.data('format') || 'dd-mm-yy'
        }, options || {});

        var self = this;
        var rangeType = this.rangeType(element);
        var value = this.val(element);

        // Some daterange are a clone of an active one and a datepicker is already attached dom element.
        // In order to "reuse" the cloned element with another datepicker we need to "remove" it from input
        if (options.cloneDatePickers) {
            this._clearDatePickers(element);
        }

        // TODO : use different buttonText value for begin and end datepickers
        element.find('.date-end, .date-start').datepicker({
            dateFormat:      options.format,
            showOn:          "button",
            buttonText:      gettext("Calendar"),
            buttonImage:     creme_media_url("images/icon_calendar.gif"),
            buttonImageOnly: true
        });

        rangeType.on('change', function(e) {
            self._onTypeChange(element, $(this).val());
        });

        this.startDate(element).on('change', function() {
            self._updateInput(element);
        });

        this.endDate(element).on('change', function() {
            self._updateInput(element);
        });

        if (Object.isEmpty(value)) {
            this._updateInput(element);
            value = this.val(element);
        }

        this._updateRangeFields(element, value);
        element.addClass('widget-ready');
    },

    endDate: function(element) {
        return element.find('.date-end');
    },

    startDate: function(element) {
        return element.find('.date-start');
    },

    rangeType: function(element) {
        return element.find('.range-type');
    },

    _onTypeChange: function(element, value) {
        var isCustomRange = Object.isEmpty(value);

        element.find('.daterange-inputs').toggleClass('hidden', !isCustomRange);

        if (!isCustomRange) {
            this.endDate(element).val('');
            this.startDate(element).val('');
        }

        this._updateInput(element);
    },

    _clearDatePickers: function(element) {
        element.find('.daterange-input.hasDatepicker')
                    .removeAttr('id')
                    .removeClass('hasDatepicker');

        element.find('img.ui-datepicker-trigger').remove();
    },

    dependencies: function(element) {
        return [];
    },

    reload: function(element, url, cb, error_cb, sync) {
        if (cb !== undefined) {
            cb(element);
        }
    },

    _updateInput: function(element) {
        var input = creme.widget.input(element);
        var data = JSON.stringify({
            type:  this.rangeType(element).val(),
            start: this.startDate(element).val(),
            end:   this.endDate(element).val()
        });

        if (data !== input.val()) {
            input.val(data).trigger('change');
        }
    },

    _updateRangeFields: function(element, data) {
        var defaultData = {type: '', start: null, end: null};

        try {
            data = Object.isString(data) ? JSON.parse(data) : data || defaultData;
        } catch (e) {
            data = defaultData;
        }

        // TODO : use this method instead. parse json if value is a string and
        // a default value if undefined or invalid json.
        // var values = creme.widget.cleanval(value, {'type':'', 'start':null, 'end':null});
        this.endDate(element).val(data.end || '');
        this.startDate(element).val(data.start || '');
        this.rangeType(element).val(data.type || '').trigger('change');
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.widget.input(element).val();
        }

        creme.widget.input(element).val(value);
        this._updateRangeFields(element, value);
    }
});

}(jQuery));
