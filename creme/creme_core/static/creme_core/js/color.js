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

(function($) {"use strict";

creme.color = creme.color || {};

creme.color.HEXtoRGB = function(hex) {//Extracted from gccolor-1.0.3 plugin
    var hex = parseInt(((hex.indexOf('#') > -1) ? hex.substring(1) : hex), 16);
    return {r: hex >> 16, g: (hex & 0x00FF00) >> 8, b: (hex & 0x0000FF)};
};

creme.color.luminance = function(r, g, b) {
    r = Math.pow (r / 255, 2.2);
    g = Math.pow (g / 255, 2.2);
    b = Math.pow (b / 255, 2.2);

    return 0.212671*r + 0.715160*g + 0.072169*b;
};

creme.color.contrast = function(r, g, b, r2, g2, b2) {
    var luminance1 = creme.color.luminance(r, g, b);
    var luminance2 = creme.color.luminance(r2, g2, b2);
    return (Math.max(luminance1, luminance2) + 0.05) / (Math.min(luminance1, luminance2) + 0.05);
};

creme.color.maxContrastingColor = function(r, g, b) {
    var withWhite = creme.color.contrast(r, g, b, 255, 255, 255);
    var withBlack = creme.color.contrast(r, g, b, 0, 0, 0);

    if (withWhite > withBlack)
        return 'white';
    return 'black'; //TODO: ? 'white': 'black';
};
}(jQuery));
