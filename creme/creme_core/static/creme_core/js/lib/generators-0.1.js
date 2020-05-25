/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2012 Hybird
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

(function() {
"use strict";

window.ArrayTools = {
    get: function(data, index, default_value) {
        var value = null;

        if (index === -1 || index === (data.length - 1)) {
            value = data.slice(index);
        } else {
            value = data.slice(index, index + 1);
        }

        return value.length ? value[0] : default_value;
    },

    set: function(data, index, value) {
        if (index >= 0) {
            data[index] = value;
            return data;
        }

        if (index >= -data.length) {
            data.splice(index, 1, value);
            return data;
        }

        var prev = [];
        prev[-(data.length + index + 1)] = value;

        Array.prototype.unshift.apply(data, prev.reverse());
        return data;
    },

    remove: function(data, index) {
        return data.splice(index, 1)[0];
    },

    sum: function(data, start, end) {
        var total = 0.0;
        data = (start !== undefined) ? data.slice(start, end) : data;

        data.forEach(function(value) {
            total += window.isNaN(value) ? 0.0 : value;
        });
        return total;
    },

    swap: function(data, prev, next) {
        var next_val = this.get(data, next);
        var prev_val = this.get(data, prev);

        this.set(data, next, prev_val);
        this.set(data, prev, next_val);

        return data;
    }

/* TODO : never used ?
        insertOrReplace: function(data, replaceIndex, insertIndex, value) {
            if (insertIndex !== undefined) {
                data.splice(insertIndex, 0, value);
            } else {
                ArrayTools.set(data, replaceIndex, value);
            }

            return data;
        }
*/
};

window.Generator = function() {
    this._getter = undefined;
    this._processor = undefined;
};

Generator.prototype = {
    _next: function(entry, index, data) {
        var value = this._getter ? this._getter.bind(this)(entry, index, data) : entry;

        if (value !== undefined && this._processor) {
            value = this._processor.bind(this)(value, index, data);
        }

        return value;
    },

    get: function(getter) {
        if (getter === undefined) {
            return this._getter;
        }

        if (typeof getter === 'number') {
            var _index = getter;
            this._getter = function(entry, index, data) {
                return ArrayTools.get(entry, _index);
            };
        } else if (Object.isFunc(getter)) {
            this._getter = getter;
        } else if (getter !== null) {
            var _key = getter;
            this._getter = function(entry, index, data) {
                return entry[_key];
            };
        } else {
            this._getter = undefined;
        }

        return this;
    },

    each: function(processor) {
        if (processor === undefined) {
            return this._processor;
        }

        this._processor = Object.isFunc(processor) ? processor : undefined;
        return this;
    },

    iterator: function() {
        var self = this;

        return function(element, index, array) {
            return self._next(element, index, array);
        };
    }
};

window.GeneratorTools = {
    array: {
        swap: function(prev, next) {
            return function(value, index, data) {
                return ArrayTools.swap(value.slice(), prev, next);
            };
        },

        ratio: function(valueIndex, total, ratio, targetIndex) {
            return function(value, index, data) {
                var val = (ArrayTools.get(value, valueIndex, 0.0) * ratio) / total;
                var array = value.slice();

                if (targetIndex !== undefined) {
                    array.splice(targetIndex, 0, val);
                } else {
                    ArrayTools.set(array, valueIndex, val);
                }

                return array;
            };
        },

        format: function(format, targetIndex) {
            return function(value, index, data) {
                var array = value.slice();
                array.splice(targetIndex !== undefined ? targetIndex : value.length, 0, format.format(value));

                return array;
            };
        }
    }
};
}());
