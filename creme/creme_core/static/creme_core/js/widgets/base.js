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

creme.widget = {
    _widgets : {},

    ready: function() {
        var self = creme.widget;

        $('.ui-creme-widget').each(function() {
            self.activate($(this));
        });
    },

    register: function(name, widget) {
        creme.widget._widgets[name] = widget;
    },

    clone: function(element, events) {
        var copy = element.clone(events);
        creme.widget.activate(copy, true);
        return copy;
    },

    activate: function(element, force, widget) {
        var self = creme.widget;

        if (element.hasClass('widget-active') && !force)
            return;

        widget = (widget == undefined) ? self._widgets[element.attr('widget')] : widget;

        if (widget == undefined)
            return;

        //if (force)
        //    console.log('force activation', element);

        if (element.data('widget') == undefined) {
            element.data('widget', widget);
            element.data('widget-options', creme.widget.parseopt(element, widget.options, {}));
            element.addClass('widget-active');
        }

        $('.ui-creme-widget', element).each(function() {
            self.activate($(this), force);
        });


        element.trigger('widget-active');

        if (element.hasClass('widget-auto')) {
            element.removeClass('widget-auto');
            element.data('widget').init(element);
        }
    },

    template: function(template, values) {
        if ((template == undefined) || (values == undefined))
            return;

        var entries = template.match(/\$\{[\w\d]+\}/g);
        var res = new String(template);

        if (typeof values != 'function')
            getter = function(key) {return values[key];}
        else
            getter = values;

        for(var i = 0; i < entries.length; i++) {
            var entry = entries[i];
            var key = entry.slice(2, -1);
            res = res.replace(entry, getter(key));
        }

        return res;
    },

    parseopt: function(element, defaults, options, attributes) {
        var opts = {};

        if (attributes === undefined) {
            attributes = [];

            for(var optname in defaults) {
                attributes.push(optname);
            }
        }

        for (var i = 0; i < attributes.length; ++i) {
            var opt = element.attr(attributes[i]);

            if (opt !== undefined)
                opts[attributes[i]] = opt;
        }

        opts = $.extend(defaults, opts);
        opts = (options !== undefined) ? $.extend(opts, options) : opts;

        //console.log(element, opts, defaults);
        return opts;
    },

    declare: function(name, parent, object) {
        res = (parent != undefined) ? $.extend(parent, object, true) : object;

        res.init = function(element, options, cb, sync) {
            var opts = creme.widget.parseopt(element, element.data('widget').options, options);
            element.data('widget-options', opts);
            element.data('widget')._create(element, opts, cb, sync);
        }

        creme.widget.register(name, res);
        return res;
    },

    parseval: function(value, parser) {
        if ((value != undefined) && (typeof value === 'string') && (parser != undefined)) {
            return parser(value);
        }

        return value;
    },

    val: function(elements, values, parser) {
        values = creme.widget.parseval(values, parser);

        if (values !== undefined) {
            var index = 0;

            if (values === null) {
                return;
            }

            elements.each(function() {
                var value = ((values != null) && index < values.length) ? values[index] : null;
                $(this).data('widget').val($(this), value);
                ++index;
            });
        } else {
            var res = [];

            elements.each(function() {
                res.push($(this).data('widget').val($(this)));
            });

            return res;
        }
    },

    input: function(element) {
        return $('input.ui-creme-input.' + $(element).attr('widget'), element);
    },

    options: function(element) {
        return element.data('widget-options');
    },

    get: function(element) {
        return element.data('widget');
    }
}

$(document).ready(function() {
    creme.widget.ready();
});
