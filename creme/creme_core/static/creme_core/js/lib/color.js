/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

var __namedColors = {
    black:   "#000000",
    silver:  "#c0c0c0",
    gray:    "#808080",
    white:   "#ffffff",
    maroon:  "#800000",
    red:     "#ff0000",
    purple:  "#800080",
    fuchsia: "#ff00ff",
    green:   "#008000",
    lime:    "#00ff00",
    olive:   "#808000",
    yellow:  "#ffff00",
    navy:    "#000080",
    blue:    "#0000ff",
    teal:    "#008080",
    aqua:    "#00ffff",
    orange:  "#ffa500"
};

function parseCSSColorName(value, cached) {
    var hex = __namedColors[value];

    if (hex === undefined) {
        var ctx = document.createElement('canvas').getContext('2d');
        ctx.fillStyle = value;
        hex = ctx.fillStyle;

        if (hex === '#000000' && value.toLowerCase() !== 'black') {
            throw new Error('"${0}" is not a valid css named color'.template([value]));
        }

        __namedColors[value] = hex;
    }

    return hex;
}

window.RGBColor = function(value) {
    if (Object.isString(value)) {
        value = value.toLowerCase();

        if (value.startsWith('#')) {
            this.hex(value);
        } else if (value.startsWith('rgb(')) {
            this.rgb(value);
        } else if (value.match(/[a-z]+$/)) {
            this.hex(parseCSSColorName(value));
        } else {
            throw new Error('"${0}" is not a RGB css value'.template([value]));
        }
    } else if (isFinite(value)) {
        this.decimal(value);
    } else if (Array.isArray(value)) {
        this.rgb(value);
    } else if (value instanceof RGBColor) {
        this.set(value);
    } else {
        this.set(Object.assign({r: 0, g: 0, b: 0}, value));
    }
};

RGBColor.prototype = {
    clone: function() {
        return new RGBColor(this);
    },

    set: function(color) {
        this.r = Math.trunc(color.r || 0);
        this.g = Math.trunc(color.g || 0);
        this.b = Math.trunc(color.b || 0);
        return this;
    },

    get: function() {
        return {r: this.r, g: this.g, b: this.b};
    },

    toString: function() {
        return '#' + this.hex();
    },

    rgb: function(value) {
        if (value === undefined) {
            return 'rgb(' + [this.r, this.g, this.b].join(',') + ')';
        }

        if (Object.isString(value)) {
            value = value.toLowerCase();

            if (value.startsWith('rgb(')) {
                return this.rgb(value.slice(4, value.length - 1).split(',').map(parseFloat));
            } else {
                throw new Error('"${0}" is not a RGB css value'.template([value]));
            }
        } else if (Array.isArray(value)) {
            this.set({r: value[0], g: value[1], b: value[2]});
        } else {
            throw new Error('"${0}" is not a RGB css value'.template([value]));
        }

        return this;
    },

    hex: function(value) {
        if (value === undefined) {
            var hex = this.decimal().toString(16);
            hex = '000000'.substr(0, 6 - hex.length) + hex;
            return hex.toUpperCase();
        }

        if (Object.isString(value) && value.match(/^(#)?[0-9a-f]{6,6}$/i)) {
            value = parseInt((value.indexOf('#') === 0 ? value.substring(1) : value), 16);
        } else {
            throw new Error('"${0}" is not a RGB hexadecimal value'.template([value]));
        }

        return this.decimal(value);
    },

    decimal: function(value) {
        if (value === undefined) {
            return ((this.r << 16) + (this.g << 8) + this.b);
        }

        if (isFinite(value) && value >= 0 && value <= 0xFFFFFF) {
            this.r = value >> 16;
            this.g = (value & 0x00FF00) >> 8;
            this.b = (value & 0x0000FF);
        } else {
            throw new Error('"${0}" is not a RGB decimal value'.template([value]));
        }

        return this;
    },

    hsl: function() {
        var r = this.r / 255;
        var g = this.g / 255;
        var b = this.b / 255;

        var max = Math.max(r, g, b);
        var min = Math.min(r, g, b);
        var lightness = (max + min) / 2;
        var brightness = max;
        var hue = 0;
        var saturation = 0;

        if (max === min) {
            return {
                h: 0,
                s: 0,
                l: _.absRound(lightness * 100),
                b: _.absRound(brightness * 100)
            };
        };

        var d = max - min;

        saturation = d / ((lightness <= 0.5) ? (max + min) : (2 - d));

        if (max === r) {
            hue = (g - b) / d + (g < b ? 6 : 0);
        } else if (max === g) {
            hue = ((b - r) / d + 2);
        } else {
            hue = ((r - g) / d + 4);
        }

        hue = hue / 6;

        return {
            h: _.absRound(hue * 360),
            s: _.absRound(saturation * 100),
            l: _.absRound(lightness * 100),
            b: _.absRound(brightness * 100)
        };
    },

    lightness: function() {
        var r = this.r / 255;
        var g = this.g / 255;
        var b = this.b / 255;

        var max = Math.max(r, g, b);
        var min = Math.min(r, g, b);
        var lightness = (max + min) / 2;

        return _.absRound(lightness * 100);
    },

    intensity: function(gamma) {
        gamma = gamma || 2.2;  // CRT gamma (I wonder if still usefull)

        var r = Math.pow(this.r / 255, gamma);
        var g = Math.pow(this.g / 255, gamma);
        var b = Math.pow(this.b / 255, gamma);

        var l = 0.212671 * r + 0.715160 * g + 0.072169 * b;
        return _.clamp(_.scaleRound(l, 3), 0, 1);
    },

    grayscale: function(gamma) {
        var c = _.clamp(this.intensity(gamma) * 255, 0, 255);
        return new RGBColor({r: c, g: c, b: c});
    },

    contrast: function(color, gamma) {
        var l1 = this.intensity(gamma);
        var l2 = new RGBColor(color).intensity(gamma);

        // contrast ratio 1 to 21
        var c = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
        return _.clamp(_.scaleRound(c, 3), 1, 21);
    },

    isDark: function(gamma) {
        return this.contrast(0, gamma) < 10;
    },

    foreground: function(gamma) {
        return this.isDark(gamma) ? new RGBColor(0xFFFFFF) : new RGBColor(0x000000);
    }
};

}());
