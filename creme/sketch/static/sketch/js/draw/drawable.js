/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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

creme.D3Drawable = creme.component.Component.sub({
    defaultProps: {},

    _init_: function(options) {
        this.props($.extend({}, this.defaultProps, options || {}));
    },

    drawAll: function(selection) {
        var self = this;

        return selection.each(function(datum, i, nodes) {
            self.draw(this, datum, i, nodes);
        });
    },

    draw: function(d, i) {
        throw new Error('Not implemented');
    },

    props: function(props) {
        if (props === undefined) {
            return $.extend({}, this._props);
        }

        this._props = $.extend(this._props || {}, props);
        return this;
    },

    prop: function(name, value) {
        if (value === undefined) {
            return this._props[name];
        } else {
            this._props[name] = value;
            return this;
        }
    }
});

creme.d3Drawable = function(options) {
    options = options || {};

    var props = options.props || [];
    var instance = options.instance;

    Assert.is(instance, creme.D3Drawable, 'Must be a creme.D3Drawable');

    function renderer(selection) {
        return instance.drawAll(selection);
    }

    renderer.prop = function(name, value) {
        var res = instance.prop(name, value);
        return value === undefined ? res : this;
    };

    renderer.props = function(props) {
        var res = instance.props(props);
        return props === undefined ? res : this;
    };

    props.forEach(function(name) {
        renderer[name] = function(value) {
            var res = instance.prop(name, value);
            return value === undefined ? res : this;
        };
    });

    return renderer;
};

}(jQuery));
