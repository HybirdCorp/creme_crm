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

creme.d3ColorRange = function(colors, options) {
    if (Array.isArray(colors)) {
        return colors;
    } else if (Object.isFunc(colors)) {
        return colors(options);
    } else {
        return [colors];
    }
};

creme.d3SpectralColors = function(options) {
    options = Object.assign({
        start: 0,
        step: 1.0,
        size: 2
    }, options || {});

    return d3.quantize(function(t) {
        return d3.interpolateSpectral(t * options.step + options.start);
    }, Math.max(options.size, 2));
};

creme.d3Colorize = function() {
    var props = {
         scale: function(d) { return 'black'; },
         accessor: function(d) { return d.x; }
    };

    function colorize(data) {
        return data.map(function(d, i) {
            var color = props.color ? props.color(d) : d.color;
            var textColor = props.textColor ? props.textColor(d) : d.textColor;
            var value = props.accessor ? props.accessor(d, i) : d;

            d.color = color || props.scale(value);

            var rgbColor = new RGBColor(d.color);
            d.isDarkColor = rgbColor.isDark();

            if (textColor) {
                d.textColor = textColor;
            } else {
                d.textColor = d.isDarkColor ? 'white' : 'black';
            }

            return d;
        });
    }

    colorize.scale = function(scale) {
        props.scale = scale;
        return colorize;
    };

    colorize.color = function(color) {
        props.color = color;
        return colorize;
    };

    colorize.textColor = function(color) {
        props.textColor = color;
        return colorize;
    };

    colorize.accessor = function(accessor) {
        props.accessor = accessor;
        return colorize;
    };

    return colorize;
};

}());
