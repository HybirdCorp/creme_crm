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

creme.widget.PolymorphicSelect = creme.widget.declare('ui-creme-polymorphicselect', {
    options: {
        type: "",
    },

    _create: function(element, options, cb, sync) {
        var self = creme.widget.PolymorphicSelect;

        self._selector_change = function() {
            self._update(element);
        }

        var value = self.val(element);

        if (!value) {
            self._update(element);
            value = self.val(element);
        }

        self._update_selector(element, value);

        if (cb != undefined) cb(element);
    },

    _update_selector: function(element, value) {
        var self = creme.widget.PolymorphicSelect;

        var old_values = self.val(element);
        var values = creme.widget.cleanval(value);

        values['type'] = values['type'] === null ? old_values['type'] : values['type'];

        self._toggle_selector(element, values['type'], values['value'], {});
        self._update(element);

//        console.log("_update_selector > value  >", value, ' (type="' + (typeof value) + '")');
//        console.log("                 > real   >", self.val(element));
//        console.log("                 > widget >", $('.ui-creme-widget.polymorphicselect-widget', element).attr('input-type'));
    },

    _update: function(element) {
        var self = creme.widget.PolymorphicSelect;
        var widget = $('.ui-creme-widget.polymorphicselect-widget', element);
        var value = null;

        if (creme.widget.is_valid(widget)) {
            value = '{"type":"' + widget.attr('input-type') + '", "value":' + widget.data('widget').jsonval(widget) + '}';
        } else {
            value = '{"type":null, "value":null}';
        }

        creme.widget.input(element).val(value).change();
    },

    _toggle_selector: function(element, type, value, options) {
         var self = creme.widget.PolymorphicSelect;
         var current = $('.ui-creme-widget.polymorphicselect-widget', element);

         if (creme.widget.is_valid(current) && type === current.attr('type')) {
             current.data('widget').val(current, value);
             return;
         }

         element.removeClass('widget-ready');

         var model = $('.inner-polymorphicselect-model li[input-type="' + type + '"] > .ui-creme-widget', element);

         if (!creme.widget.is_valid(model)) {
             var default_container = $('.inner-polymorphicselect-model li.default:first');
             model = $('> .ui-creme-widget', default_container);
         }

         var widget = creme.widget.get(model).clone(model);
         widget.data('widget').val(widget, value);
         widget.data('widget').init(widget, options, undefined, undefined, true);

         widget.addClass("polymorphicselect-widget")
                .attr('style', 'display:inline;')
                .attr('input-type', type);

         if (creme.widget.is_valid(current)) {
             current.unbind('change', self._widget_change);
             current.remove();
         }

         element.append(widget);
         widget.bind('change', self._selector_change);

         element.addClass('widget-ready');
    },

    reload: function(element, url, cb, error_cb, sync) {
        var self = creme.widget.PolymorphicSelect;
        var values = self.val(element);

        if (values['type'] === url)
            return;

        values['type'] = url;
        self.val(element, values);

        //console.log("pselect.reload > value >", self.val(element));

        if (cb != undefined) cb(element);
    },

    val: function(element, value) {
        var self = creme.widget.PolymorphicSelect;

        if (value === undefined) {
            return creme.widget.cleanval(creme.widget.input(element).val(), {"type":null, "value":null});
        }

        //console.log("pselect.val >", element, "new=" + $.toJSON(value), "old=" + creme.widget.input(element).val());
        self._update_selector(element, value);
        //console.log("val > end");
    },

    clone: function(element) {
        var self = creme.widget.PolymorphicSelect;
        var copy = creme.widget.clone(element);
        return copy;
    }
});
