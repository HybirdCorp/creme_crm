/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2025 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

var __frozenStatics = ['prototype', '__super__', 'sub', 'create'];

creme.component = {};

creme.component.extend = function(Parent, content) {
    Parent = Parent || Object;
    content = content || {};

    var prop;
    var NewClass = function() {
        if (this._init_) {
            this._init_.apply(this, arguments);
        } else if (Parent.prototype._init_) {
            Parent.prototype._init_.apply(this, arguments);
        }
    };

    // inherit parent prototype and add changes
    NewClass.prototype = Object.create(Parent.prototype);
    NewClass.prototype.constructor = NewClass;

    // store parent prototype and force constructor (needed by some browsers).
    NewClass.__super__ = Parent.prototype;

    // convenient static method for subclass
    NewClass.sub = function(content) {
        return creme.component.extend(NewClass, content);
    };

    // copy other static fields from parent class (Thx Leaflet :))
    for (prop in Parent) {
        if (Parent.hasOwnProperty(prop) && __frozenStatics.indexOf(prop) === -1) {
            NewClass[prop] = Parent[prop];
        }
    }

    for (prop in content) {
        NewClass.prototype[prop] = content[prop];
    }

    return NewClass;
};

creme.component.Component = creme.component.extend(Object, {
    _init_: function() {},

    _super_: function(constructor, method) {
        if (method !== undefined) {
            return constructor.prototype[method].apply(this, Array.from(arguments).slice(2));
        }

        return Object.proxy(constructor.prototype, this);
    },

    is: function(constructor) {
        return Object.isSubClassOf(this, constructor); // creme.component.is(Object.getPrototypeOf(this).constructor, constructor);
    }
});
}(jQuery));
