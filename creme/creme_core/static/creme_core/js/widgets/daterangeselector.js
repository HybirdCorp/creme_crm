/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.widget.DateRangeSelector = creme.widget.declare('ui-creme-daterange-selector', {
    options: {
          date_format: 'dd-mm-yy'
    },

    _get_end: function(element) {
        return $('.date-end', element);
    },

    _get_start: function(element) {
        return $('.date-start', element);
    },

    _get_type: function(element) {
        return $('.range-type', element);
    },

    _create: function(element, options, cb, sync) {
        var self = creme.widget.DateRangeSelector;
        var value = self.val(element);
        var $datespan = $('span.daterange-inputs', element);
        var datepicker_options = {dateFormat:      options['date_format'],
                                  showOn:          "button",
                                  buttonImage:     media_url("images/icon_calendar.gif"),
                                  buttonImageOnly: true
                                 }

        self._get_type(element).bind('change', function() {
                if ($(this).val()) {
                    $datespan.hide();
                } else {
                    $datespan.show();
                }

                self._update(element);
            });

        // Some daterange are a clone of an active one and a datepicker is already attached dom element. 
        // In order to "reuse" the cloned element with another datepicker we need to "remove" it from input
        self._clean_daterpickers($datespan);

        $('.daterange-input', $datespan).bind('change', function() {self._update(element);})
                                        .datepicker(datepicker_options);

        if (!value) {
            self._update(element);
            value = self.val(element);
        }

        self._update_inputs(element, value);
        element.addClass('widget-ready');
    },

    _clean_daterpickers: function(datespan) 
    {
    	$('.daterange-input', datespan).removeAttr('id')
    								   .removeClass('hasDatepicker');

    	$('img.ui-datepicker-trigger', datespan).remove();
    },
    
    _update: function(element) {
        var self = creme.widget.DateRangeSelector;
        creme.widget.input(element).val(self.val(element)).change();
    },

    reload: function(element, url, cb, error_cb, sync) {
        if (cb != undefined) cb(element);
    },

    _update_inputs: function(element, value) {
        var self = creme.widget.DateRangeSelector;
        var type = value['type'];

        // TODO : use this method instead. parse json if value is a string and
        // a default value if undefined or invalid json.
        //var values = creme.widget.cleanval(value, {'type':'', 'start':null, 'end':null});

        if (type !== undefined) {
            self._get_type(element).val(type).change();
            self._get_start(element).val(value['start']).change();
            self._get_end(element).val(value['end']).change();
        }
    },

    val: function(element, value) {
        var self = creme.widget.DateRangeSelector;

        if (value === undefined) {
        	// TODO : returns the hidden input value instead. easier for bug detection :))
        	// var res = creme.widget.input(element).val();
        	// return (!res) ? null : res;
            return $.toJSON({'type':  self._get_type(element).val(),
                             'start': self._get_start(element).val(),
                             'end':   self._get_end(element).val()
                            });
        }

        self._update_inputs(element, value);
    },

    clone: function(element) {
        return creme.widget.clone(element);
    }
});
