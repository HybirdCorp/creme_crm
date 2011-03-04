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

creme.widget.ChainedSelect = creme.widget.declare('ui-creme-chainedselect', {
    options : {
        json:true
    },

    _create: function(element, options) {
        var self = creme.widget.ChainedSelect;

        $('.ui-creme-widget', element).each(function() {
            $(this).data('widget').init($(this), {url:''}, undefined, true);
        });

        self._dependency_change = function() {
        	//console.log('element:' + $(this).parent().attr('chained-name') + ' has changed. val:' + $(this).val());
            self._reload_dependencies(element, $(this).parent().attr('chained-name'));
            self._update(element);
        };
        
        $('.ui-creme-widget', element).bind('change', self._dependency_change);

        $('img.reset', element).bind('click', function() {
            self.reset(element);
        });

        var value = self.val(element);

        if (!value) {
            self._update(element);
            value = self.val(element);
        }
        
        self._update_selectors(element, value);
        element.addClass('widget-ready');
    },

    _update: function(element) 
    {
        var self = creme.widget.ChainedSelect;
        var values = []

        $('.ui-creme-widget.widget-active', element).each(function() 
        {
        	var value = $(this).data('widget').val($(this));
        	var name = $(this).parent().attr('chained-name');
        	
        	//console.log('chainedselect._update > value="' + name + '", type=' + value);
        	values.push('"' + name + '":' + ((typeof value === 'string') ? '"' + value + '"' : value));
        });

        creme.widget.input(element).val('{' + values.join(',') + '}');
    },

    _buildurl: function(element, url)
    {
        var self = creme.widget.ChainedSelect;
        return creme.widget.template(url, function(key) {
            //console.log("chainedselect._buildurl > " + key + " > " + item.val());
            return element.data('widget').val(element);
        });
    },
    
    _update_selectors: function(element, value)
    {
    	var self = creme.widget.ChainedSelect;

    	//console.log("ChainedSelect._update_selectors > value  : '" + value + "'");

    	if (value === undefined)
    		return;

        values = (typeof value !== 'object') ? creme.widget.parseval(value, creme.ajax.json.parse) : value;

        //console.log("ChainedSelect._update_selectors > values : " + values + " [type:" + (typeof values) + ", value : '" + value + "' [type:" + (typeof values) + "]");

        if (values === null || typeof values !== 'object')
        	return;

        $('.ui-creme-widget', element).each(function() {
        	var item = $(this);
            var itemval = (values) ? values[item.parent().attr('chained-name')] : null;
            itemval = (itemval) ? itemval : '';
            
            //console.log("ChainedSelect._update_selectors >", item, " > ", itemval);
            
            item.data('widget').val(item, itemval);
        });
    },

    _reload_dependencies: function(element, name)
    {
        var self = creme.widget.ChainedSelect;
        
        //$('.ui-creme-widget', element).unbind('change', self._dependency_change);
        
        var item = $('li[chained-name="' + name + '"] .ui-creme-widget.widget-active', element);
        //console.log('chainedselect._reload_dependencies > ' + name + ':', item);

        $('.ui-creme-widget[url*="${' + name + '}"]', element).each(function() {
             var dep = $(this);
             var url = self._buildurl(item, dep.attr('url'));

             //console.log('chainedselect._reload_dependencies > ' + dep.parent().attr('chained-name') + ':' + item + ' > url:' + url);
             dep.data('widget').reload(dep, url, undefined, undefined, true);
         });
        
        //$('.ui-creme-widget', element).bind('change', self._dependency_change);
    },

    reset: function(element) {
    	var self = creme.widget.ChainedSelect;
        self.val(element, '{}');
    },

    val: function(element, value)
    {
        var self = creme.widget.ChainedSelect;

        if (value === undefined) {
        	var res = creme.widget.input(element).val();
        	return (!res) ? null : res;
        }
        
        self._update_selectors(element, value);
        self._update(element);
    },

    clone: function(element)
    {
        var self = creme.widget.ChainedSelect;
        var copy = creme.widget.clone(element);
        
        var value = self.val(copy);

        if (!value) {
        	self._update(copy);
        }
        
        return copy;
    }
});
