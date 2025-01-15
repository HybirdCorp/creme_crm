/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2023-2025  Hybird

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

(function() {
"use strict";

creme.d3BisectScale = function(getter) {
    var bisect = d3.bisector(getter).center;
    var props = {
        scale: null
    };

    function invertLinear(data, pos) {
        return bisect(data, props.scale.invert(pos), 0);
    }

    function invertOrdinal(data, pos) {
        var scale = d3.scaleLinear([0, data.length], props.scale.range());
        var index = Math.max(0, Math.min(Math.floor(scale.invert(pos)), data.length - 1));
        return getter(data[index]);
    }

    function invert(data, pos) {
        return props.scale.invert ? invertLinear(data, pos) : invertOrdinal(data, pos);
    }

    invert.scale = function(scale) {
        if (scale === undefined) {
            return props.scale;
        } else {
            props.scale = scale;
            return invert;
        }
    };

    return invert;
};

}());
