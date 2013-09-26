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

creme.component= {};

creme.object = {
    isnone: function(obj) {
        return obj === undefined || obj === null;
    },

    isempty: function(obj) {
        return this.isnone(obj) || obj.length === 0 || (obj !== 0 && $.isEmptyObject(obj))
    },

    invoke: function()
    {
        if (arguments.length == 0)
            return;

        var cb = arguments[0];

        if (typeof cb !== 'function')
            return;

        var args = [];

        for(var i = 1; i < arguments.length; ++i)
            args.push(arguments[i]);

        return cb.apply(this, args);
    },

    delegate: function()
    {
        if (arguments.length < 2)
            return;

        var delegate = arguments[0];
        var cb = arguments[1];
        var args = [];

        if (this.isempty(delegate) || typeof delegate !== 'object')
            return;

        if (typeof cb === 'string')
            cb = delegate[cb];

        if (typeof cb !== 'function')
            return;

        for(var i = 2; i < arguments.length; ++i)
            args.push(arguments[i]);

        return cb.apply(delegate, args);
    },

    build_callback: function(script, parameters)
    {
        if (typeof script === 'function')
            return script;

        var parameters = parameters || [];

        try {
            var script = script ? 'cb = function(' + parameters.join(',') + ') {' + (script.indexOf('return') === -1 ? 'return ' : '') + script + '};' : undefined;
            return script ? eval(script) : undefined;
        } catch(e) {
            throw Error('Invalid callback script : ' + e);
        }
    },

    deferred_start: function(element, name, func, delay)
    {
        var key = 'deferred__' + name;
        var previous = element.data(key);

        if (previous !== undefined)
            previous.reject();

        var deferred = $.Deferred();

        $.when(deferred.promise()).then(function(status) {
            element.removeData(key);
            creme.object.invoke(func, element, status);
        }, null, null);

        element.data(key, deferred);

        if (delay) {
            window.setTimeout(function() {deferred.resolve();}, delay);
        } else {
            deferred.resolve();
        }

        return deferred;
    },

    deferred_cancel: function(element, name)
    {
        var key = 'deferred__' + name;
        var previous = element.data(key);

        if (previous !== undefined) {
            element.removeData(key);
            previous.reject();
        }

        return previous;
    },

    uuid: function() {
        return $.uidGen({prefix: 'jqplot_target_', mode:'random'})
    },

    isFalse: function(value) {
        return Object.isNone(value) || value === false;
    },

    isTrue: function(value) {
        return !Object.isNone(value) && value !== false;
    }
}

creme.object.JSON = function() {}

creme.object.JSON.prototype = {
    encode: function(data)
    {
        if (typeof jQuery.toJSON !== 'function') {
            throw 'not implemented !';
        }

        return jQuery.toJSON(data);
    },

    isJSON: function(data)
    {
        // Make sure the incoming data is actual JSON
        // Logic borrowed from http://json.org/json2.js
        return typeof data === 'string' && 
               (/^[\],:{}\s]*$/.test(data.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
                                         .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
                                         .replace(/(?:^|:|,)(?:\s*\[)+/g, "")));
    },

    decode: function(data, defaults)
    {
        if (defaults !== undefined) {
            try {
                this.decode(data);
            } catch(e) {
                return defaults;
            }
        }

        if ( typeof data !== "string" || !data) {
            throw 'Invalid data type or empty string';
        }

        // Make sure leading/trailing whitespace is removed (IE can't handle it)
        data = jQuery.trim(data);

        try {
            if (window.JSON && window.JSON.parse)
                return window.JSON.parse(data);
        } catch(err) {
            throw 'JSON parse error: ' + err;
        }

        var isvalid = this.isJSON(data);

        if (!isvalid)
            throw 'JSON parse error (fallback)';

        try {
            // Try to use the native JSON parser first
            return (new Function("return " + data))();
        } catch(err) {
            throw 'JSON parse error (fallback): ' + err;
        }
    }
};

creme.widget = {};

creme.widget.Widget = function() {
    return {
        options:{},
        arguments:{},

        _create: function(element, options, cb, sync) {},
        _destroy: function(element) {},

        destroy: function(element) {
            creme.widget.destroy(element);
        },

        isActive: function(element) {
            return creme.widget.is_valid(element);
        },

        cleanedval: function(element)
        {
            if (!this.isActive(element))
                return null;

            var value = element.creme().widget().val();
            return creme.widget.cleanval(value, value);
        }
    };
};

$.extend(creme.widget, {
    _widgets : {},

    ready: function(root) {
        var self = creme.widget;

        $('.ui-creme-widget.widget-auto', root).each(function() {
            self.create($(this));
        });
    },

    register: function(name, widget) {
        creme.widget._widgets[name] = widget;
    },

    unregister: function(name) {
        if (creme.widget._widgets[name] !== undefined)
            delete creme.widget._widgets[name];
    },

    find: function(name) {
        return creme.widget._widgets[name];
    },

    proxy: function(element, delegate)
    {
        if (creme.object.isnone(delegate))
            return;

        var widget = {
           element: element,
           delegate: delegate,
           options: function() {
               return this.delegate.options;
           },
           arguments: function() {
               return this.delegate.arguments;
           }
        };

        (function(widget) {
            $.each(widget.delegate, function(key, value) {
                if (typeof value !== 'function' || key.match('^_.*') !== null)
                    return;

                widget[key] = function() {
                    return value.apply(widget.delegate, [widget.element].concat(Array.copy(arguments)));
                };
            });
        })(widget);

        return widget;
    },

    create: function(element, options, cb, sync)
    {
        if (element.data('CremeWidget') !== undefined)
            return;

        var widget = creme.widget.find(element.attr('widget'));

        if (typeof widget !== 'object')
            return;

        var delegate = $.extend({}, widget);
        delegate.options = creme.widget.parseopt(element, widget.options, options);
        delegate.arguments = creme.widget.parseattr(element, $.extend({'widget':'', 'class':''}, delegate.options));

        var proxy = creme.widget.proxy(element, delegate);

        element.data('CremeWidget', proxy);
        element.addClass('widget-active');

        delegate._create(element, delegate.options, function() {
            creme.object.invoke(cb);
        }, sync, delegate.arguments);

        return proxy;
    },

    destroy: function(element)
    {
        if (!creme.widget.is_valid(element))
            return element;

        element.data('CremeWidget').delegate._destroy(element);
        element.removeData('CremeWidget');
        element.removeClass('widget-ready widget-active');

        return element;
    },

    declare: function(name, object, parent)
    {
        var widget = $.extend(new creme.widget.Widget(), parent, object);
        creme.widget.register(name, widget);
        return widget;
    },

    template: function(template, values)
    {
        if (template === undefined || values === undefined)
            return template;

        var entries = template.match(/\$\{[\w\d]+\}/g);

        if (entries === null)
            return template;

        var res = new String(template);

        if (typeof values !== 'function')
            getter = function(key) {return values[key];}
        else
            getter = values;

        for(var i = 0; i < entries.length; i++)
        {
            var entry = entries[i];
            var key = entry.slice(2, -1);
            var value = getter(key);

            if (value !== undefined)
                res = res.replace(entry, getter(key));
        }

        return res;
    },

    parseattr: function(element, excludes)
    {
        var attributes = {};

        if (element.length === 0)
            return attributes;

        for(var index = 0; index < element[0].attributes.length; ++index)
        {
            var attr = element[0].attributes[index];
            attributes[attr.name] = attr.value;
        }

        var excludes = excludes || [];

        if ($.isArray(excludes))
        {
            for(var index in excludes) {
                if (attributes[excludes[index]] !== undefined)
                    delete attributes[excludes[index]];
            }
        } else {
            for(var exclude in excludes) {
                if (attributes[exclude] !== undefined)
                    delete attributes[exclude];
            }
        }

        //console.log('parseattr > attributes:', attributes, ', excludes:', $.isArray(excludes) ? excludes : Object.keys(excludes));
        return attributes;
    },

    parseopt: function(element, defaults, options)
    {
        var opts = {};

        Object.keys(defaults || {}).forEach(function(name) {
            var value = element.attr(name);

            if (value !== undefined)
                opts[name] = element.attr(name);
        });

        opts = $.extend({}, defaults, opts, options);

        //console.log('parseopt > options:', opts, ', defaults:', defaults, ', attributes:', attributes);
        return opts;
    },

    parseval: function(value, parser) {
        if ((value !== undefined) && (typeof value === 'string') && (parser !== undefined)) {
            return parser(value);
        }

        return value;
    },

    cleanval: function(value, default_value, parser) {
        var cleanparser = (parser !== undefined) ? parser : creme.ajax.json.parse;
        var result = (typeof value === 'object') ? value : creme.widget.parseval(value, cleanparser);

        return (result !== null && result !== undefined) ? result : default_value;
    },

    val: function(element, value)
    {
        var widget = $(element).creme().widget() || $(element);

        if (value === undefined)
            return widget.val();

        return widget.val(value);
    },

    values_list: function(elements, data, parser)
    {
        var values;

        if (data === undefined)
        {
            values = [];

            elements.each(function() {
                values.push(creme.widget.val($(this)));
            });

            return values;
        }

        var values = creme.widget.parseval(data, parser);

        values = (values === null) ? '' : values;
        values = (!$.isArray(values)) ? [values] : values;

        elements.each(function(index, element) {
            var value = (index < values.length) ? values[index] : '';
            creme.widget.val(element, value);
        });
    },

    input: function(element)
    {
        var query = 'input.ui-creme-input.' + $(element).attr('widget');
        var inputs = $('input.ui-creme-input.' + $(element).attr('widget'), element);

        if ($(element).is(query))
            inputs.push(element);

        return inputs;
    },

    is_valid: function(element)
    {
        if (creme.object.isempty(element))
            return false;

        return (typeof element.data === 'function') && !creme.object.isnone(element.data('CremeWidget'));
    },

    writeAttr: function(element, options)
    {
        for(var key in options)
        {
            var value = options[key];

            if (value !== undefined)
                element.attr(key, value)
        }

        return element;
    },

    buildTag: function(element, widget, options, auto)
    {
        element.addClass('ui-creme-widget')
               .addClass(widget)
               .attr('widget', widget);

        if (auto === true)
            element.addClass('widget-auto');

        if (creme.object.isempty(options))
            return element;

        return this.writeAttr(element, options);
    }
});

$.fn.creme = function() {
    var self = $(this);

    return {
        widget: function() {
            return self.data('CremeWidget');
        },

        create: function(options, cb, sync) {
            creme.widget.create(self, options, cb, sync);
        },

        destroy: function() {
            creme.widget.destroy(self);
        },

        isActive: function() {
            return creme.widget.is_valid(self);
        }
    }
};


$(document).ready(function() {
    creme.widget.ready();
});
