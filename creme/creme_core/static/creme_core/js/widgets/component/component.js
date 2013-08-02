/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.component = {}

creme.component.extend = function(parent, content)
{
    var parent = parent || Object;

    var constructor = function() {
        this._init_.apply(this, arguments);
    };

    // inherit parent prototype and add changes
    constructor.prototype = $.extend({}, parent.prototype, {
        _init_: parent.prototype._init_ || function() {}
    }, content || {});

    // store parent prototype and force constructor (needed by some browsers).
    constructor.__super__ = parent.prototype;
    constructor.prototype.constructor = constructor;

    // convenient static method for subclass
    constructor.sub = function(content) {
        return creme.component.extend(constructor, content);
    }

    return constructor;
}

creme.component.is = function(constructor, parent)
{
    if (parent === Object || constructor === parent)
        return true;

    if (constructor.prototype === undefined)
        return false;

    return (constructor.__super__ !== undefined) && creme.component.is(constructor.__super__.constructor, parent);
}

creme.component.Component = creme.component.extend(Object, {
    _init_: function() {},

    _super_: function(constructor, method)
    {
        if (method !== undefined) {
            return constructor.prototype[method].apply(this, Array.copy(arguments).slice(2));
        }

        return Object.proxy(constructor.prototype, this);
    },

    is: function(constructor) {
        return creme.component.is(Object.getPrototypeOf(this).constructor, constructor);
    }
});

