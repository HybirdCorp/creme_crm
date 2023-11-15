/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2023  Hybird

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

var EPSILON = 1e-6;
var RADIAN_RATIO = (Math.PI / 180);

function degToRad(angle) {
    return angle * RADIAN_RATIO;
}

function radToDeg(angle) {
    return angle / RADIAN_RATIO;
}

function clamp(value, lower, upper) {
    var hasLower = _.isNumber(lower);
    var hasUpper = _.isNumber(upper);

    if (hasLower && hasUpper && lower > upper) {
        return clamp(value, upper, lower);
    }

    value = hasUpper ? (upper > value ? value : upper) : value;
    return hasLower ? (lower < value ? value : lower) : value;
}

function absRound(value) {
    return (0.5 + value) << 0;
}

function scaleRound(value, precision) {
    var scale = Math.pow(10, precision || 0);
    return Math.round(value * scale) / scale;
}

function scaleTrunc(value, precision) {
    var scale = Math.pow(10, precision || 0);
    return Math.trunc(value * scale) / scale;
}

function toNumber(value) {
    return +value;
}

_.mixin({
    EPSILON: EPSILON,

    absRound: absRound,
    clamp: clamp,
    scaleRound: scaleRound,
    scaleTrunc: scaleTrunc,
    toRadian: degToRad,
    toDegree: radToDeg,
    toNumber: toNumber
});

}());
