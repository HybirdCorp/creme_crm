/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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

creme.widget.DynamicSelect = creme.widget.declare('ui-creme-dselect', {
    options: {
        url:'',
        source:function(url, cb, error_cb, sync) {
            creme.ajax.json.get(url, {fields:['id', 'unicode']}, cb, error_cb, sync);
        }
    },

    _create: function(element, options, cb, sync) {
        var self = creme.widget.DynamicSelect;
        self._fill(element, options, cb, cb, sync);
    },

    reload: function(element, url, cb, error_cb, sync) {
        var self = creme.widget.DynamicSelect;
        var opts = creme.widget.parseopt(element, self.options, {url:url});

        self._fill(element, opts, cb, error_cb, sync);
    },
    
    _staticfill: function(element, data) {
    	var self = creme.widget.DynamicSelect;
    	
    	//console.log('dselect._staticfill > ' + element + ' > ' + data);
        
    	creme.forms.Select.fill(element, data);
    	element.addClass('widget-ready');
    	
    	($('option', element).length > 1) ? element.removeAttr('disabled') : element.attr('disabled', 'disabled');
    },

    _ajaxfill: function(element, source, url, cb, error_cb, sync) 
    {
    	var self = creme.widget.DynamicSelect;
    	element.removeClass('widget-ready');
    	
        source(url,
        	   function(data) {
		           self._staticfill(element, data);
		           if (cb != undefined) cb(element);
		       },
			   function(error) {
		           element.addClass('widget-ready');
		    	   ($('option', element).length > 1) ? element.removeAttr('disabled') : element.attr('disabled', 'disabled');
		           if (error_cb != undefined) error_cb(element, error);
			   }, 
			   sync);
    },

    _fill: function(element, args, cb, error_cb, sync) {
        var self = creme.widget.DynamicSelect;
        var source = args['source'];
        var url = args['url'];
        var options = args['options'];

        if (options !== undefined) {
        	self._staticfill(element, options);
        } else if (url !== undefined && url.length > 0) {
            self._ajaxfill(element, source, url, cb, error_cb, sync);
        } else {
        	element.addClass('widget-ready');
        	($('option', element).length > 1) ? element.removeAttr('disabled') : element.attr('disabled', 'disabled');
        }

        if (cb != undefined) cb(element);
    },

    val: function(element, value) {
        //console.log(element, value, element.val());

        if (value === undefined)
        	return element.val();

        if (typeof value !== 'string')
    		value = $.toJSON(value);

        return element.val(value).change();
    },

    clone: function(element) {
    	var self = creme.widget.DynamicSelect;
        var copy = creme.widget.clone(element);
        return copy;
    }
});

//(function($) {
//    $.widget("ui.dselect", creme.widget.dselect);
//})(jQuery);
