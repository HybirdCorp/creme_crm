/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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

/*
(function($) {
"use strict";

creme.color = creme.color || {};

creme.color.HEXtoRGB = function(hex) { // Extracted from gccolor-1.0.3 plugin
    console.warn('creme.color.HEXtoRGB is deprecated; Use new RGBColor(hex) instead');
    return new RGBColor(hex).get();
};

creme.color.luminance = function(r, g, b) {
    console.warn('creme.color.luminance is deprecated; Use new RGBColor({r:r, g:g, b:b}).intensity() instead');
    return new RGBColor({r: r, g: g, b: b}).intensity();
};

creme.color.contrast = function(r, g, b, r2, g2, b2) {
    console.warn('creme.color.contrast is deprecated; Use new RGBColor({r:r, g:g, b:b}).contrast({r:r2, g:g2, b:b2}) instead');
    return new RGBColor({r: r, g: g, b: b}).contrast({r: r2, g: g2, b: b2});
};

creme.color.maxContrastingColor = function(r, g, b) {
    console.warn('creme.color.maxContrastingColor is deprecated; Use new RGBColor({r:r, g:g, b:b}).foreground() instead');
    var withWhite = new RGBColor({r: r, g: g, b: b}).contrast(0xFFFFFF);
    var withBlack = new RGBColor({r: r, g: g, b: b}).contrast(0);

    return withWhite > withBlack ? 'white' : 'black';
};

}(jQuery));
*/
