/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2015  Hybird

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

(function($) {
"use strict";

creme.utils = creme.utils || {};

creme.utils.TemplateRenderer = creme.component.Component.sub({
    tags: function(template) { return []; },
    render: function(template, values) { return template; }
});

creme.utils.TemplateDefaultRenderer = creme.utils.TemplateRenderer.sub({
    _entrypattern: /\$\{([\w\d\\.^\\s]+)\}/g,

    _attributeGetter: function(data, key) {
        var keys = Array.isArray(key) ? key : ((typeof key === 'string') ? key.split('.') : [key]);
        var value = data;

        for (var i in keys) {
            if (!Object.isNone(value) && typeof value === 'object') {
                value = value[keys[i]];
            } else {
                value = undefined;
                break;
            }

            value = Object.isFunc(value) ? value(key) : value;
        }

        return value;
    },

    tags: function(template) {
        var matches = template.match(this._entrypattern);
        var tags = {};

        if (Object.isEmpty(matches) === false) {
            matches.forEach(function(match) {
                tags[match.slice(2, -1).split('.')[0]] = 0;
                return 0;
            });
        }

        return Object.keys(tags);
    },

    render: function(template, values) {
        if (Object.isEmpty(values)) {
            return template;
        }

        var getter = this._attributeGetter.bind(this);

        return template.replace(this._entrypattern, function(match, key) {
            var value = getter(values, key);
            return value !== undefined ? value : match;
        });
    }
});

creme.utils.Template = creme.component.Component.sub({
    _init_: function(pattern, parameters, renderer) {
        this.renderer(renderer || new creme.utils.TemplateDefaultRenderer());
        this.pattern(pattern);
        this.parameters(parameters);
    },

    _resolve: function(extra) {
        extra = extra || {};

        var data = this._parameters || {};
        var resolved = {};

        if (Object.isFunc(data)) {
            this.tags().forEach(function(key) {
                resolved[key] = data(key);
            });
        } else {
            resolved = $.extend(resolved, data);
        }

        if (Object.isFunc(extra)) {
            this.tags().forEach(function(key) {
                resolved[key] = extra(key);
            });
        } else {
            resolved = $.extend(resolved, extra);
        }

        return resolved;
    },

    render: function(extra) {
        var renderer = this._renderer;
        var pattern = this._pattern;

        if (Object.isNone(renderer) || Object.isNone(pattern)) {
            return null;
        }

        return renderer.render(pattern, this._resolve(extra));
    },

    tags: function() {
        return this._tags;
    },

    _updateTags: function() {
        var renderer = this._renderer;
        var pattern = this._pattern;

        this._tags = (Object.isNone(renderer) || Object.isEmpty(pattern)) ? [] : renderer.tags(pattern);
    },

    iscomplete: function() {
        var tags = this._tags;
        var parameters = this._resolve();

        for (var i = 0; i < tags.length; ++i) {
            if (Object.isNone(parameters[tags[i]])) {
                return false;
            }
        }

        return true;
    },

    renderer: function(renderer) {
        if (renderer === undefined) {
            return this._renderer;
        }

        this._renderer = renderer;
        this._updateTags();
        return this;
    },

    pattern: function(pattern) {
        if (pattern === undefined) {
            return this._pattern;
        }

        this._pattern = pattern;
        this._updateTags();
        return this;
    },

    parameters: function(parameters) {
        return Object.property(this, '_parameters', parameters);
    },

    update: function(data) {
        // data is a string, use it as url
        if (Array.isArray(data)) {
            this.pattern(data[0]);
            this.parameters(data[1]);
        } else if (typeof data === 'object') {
            this.parameters($.extend({}, this.parameters() || {}, data));
        } else if (typeof data === 'string') {
            this.pattern(data);
        }

        return this;
    }
});

creme.utils.templatize = function(value, context) {
    var template;

    if (Object.isNone(value)) {
        template = new creme.utils.Template();
    }

    if (Object.isType(value, 'string')) {
        template = new creme.utils.Template(value);
    }

    if (value !== null && Object.isType(value, 'object') && Object.isFunc(value.is) && value.is(creme.utils.Template)) {
        template = value;
    }

    return Object.isNone(context) ? template : template.parameters(context);
};
}(jQuery));
