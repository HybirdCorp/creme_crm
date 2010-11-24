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
            $(this).data('widget').init($(this));
        });

        $('.ui-creme-widget', element).bind('change', function() {
            self.reloadDeps(element, $(this).parent().attr('chained-name'));
            self._update(element);
        });

        var value = self.val(element);

        if (!value) {
            self._update(element);
            value = self.val(element)
        }

        self.val(element, value);

        element.addClass('widget-ready');
    },

    _update: function(element) {
        var self = creme.widget.ChainedSelect;
        var values = []

        $('.ui-creme-widget.widget-active', element).each(function() {
            values.push('"' + $(this).parent().attr('chained-name') + '":"' + $(this).data('widget').val($(this)) + '"');
        });

        creme.widget.input(element).val('{' + values.join(',') + '}');
    },

    _buildurl: function(element, url)
    {
        var self = creme.widget.ChainedSelect;
        return creme.widget.template(url, function(key) {
            var item = $('li[chained-name="' + key + '"] .ui-creme-widget.widget-active', element);
            return item.data('widget').val(item);
        });
    },

    reloadDeps: function(element, name, cb, error_cb) {
        var self = creme.widget.ChainedSelect;

        $('.ui-creme-widget[url*="${' + name + '}"]', element).each(function() {
             var dep = $(this);
             var url = self._buildurl(element, dep.attr('url'));

             //console.log('reload deps ' + dep.parent().attr('chained-name') + ' url:' + url);

             if (!dep.hasClass('widget-ready')) {
                 dep.data('widget').init(dep, {url:''});
             }

             dep.data('widget').reload(dep, url, undefined, undefined, true);
         });
    },

    val: function(element, value) {
        var self = creme.widget.ChainedSelect;

        if (value !== undefined) {
            values = creme.widget.parseval(value, creme.ajax.json.parse);

            if (values === null || typeof values !== 'object')
                return;

            $('.ui-creme-widget', element).each(function() {
                var itemval = (values) ? values[$(this).parent().attr('chained-name')] : null;
                itemval = (itemval) ? itemval : null;
                $(this).data('widget').val($(this), itemval);
            });

            element.trigger('change');
        }

        res = creme.widget.input(element).val()
        return (!res) ? null : res;
    },

    clone: function(element) {
        var self = creme.widget.ChainedSelect;
        var copy = creme.widget.clone(element);
        self.val(copy, self.val(element));
        return copy;
    }
});
