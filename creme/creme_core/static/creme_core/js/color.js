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


creme.color = creme.color || {}

creme.color.HEXtoRGB = function(hex) {//Extracted from gccolor-1.0.3 plugin
    var hex = parseInt(((hex.indexOf('#') > -1) ? hex.substring(1) : hex), 16);
    return {r: hex >> 16, g: (hex & 0x00FF00) >> 8, b: (hex & 0x0000FF)};
};

// XXX: commented the 13th october 2013
// creme.utils.RGBtoHSB = function(rgb) {
//     var hsb = {};
//     hsb.b = Math.max(Math.max(rgb.r, rgb.g), rgb.b);
//     hsb.s = (hsb.b <= 0) ? 0 : Math.round(100 * (hsb.b - Math.min(Math.min(rgb.r, rgb.g), rgb.b)) / hsb.b);
//     hsb.b = Math.round((hsb.b / 255) * 100);
//     if((rgb.r == rgb.g) && (rgb.g == rgb.b)) hsb.h = 0;
//     else if(rgb.r >= rgb.g && rgb.g >= rgb.b) hsb.h = 60 * (rgb.g - rgb.b) / (rgb.r - rgb.b);
//     else if(rgb.g >= rgb.r && rgb.r >= rgb.b) hsb.h = 60  + 60 * (rgb.g - rgb.r) / (rgb.g - rgb.b);
//     else if(rgb.g >= rgb.b && rgb.b >= rgb.r) hsb.h = 120 + 60 * (rgb.b - rgb.r) / (rgb.g - rgb.r);
//     else if(rgb.b >= rgb.g && rgb.g >= rgb.r) hsb.h = 180 + 60 * (rgb.b - rgb.g) / (rgb.b - rgb.r);
//     else if(rgb.b >= rgb.r && rgb.r >= rgb.g) hsb.h = 240 + 60 * (rgb.r - rgb.g) / (rgb.b - rgb.g);
//     else if(rgb.r >= rgb.b && rgb.b >= rgb.g) hsb.h = 300 + 60 * (rgb.r - rgb.b) / (rgb.r - rgb.g);
//     else hsb.h = 0;
//     hsb.h = Math.round(hsb.h);
//     return hsb;
// };

creme.color.luminance = function(r, g, b) {
    r = Math.pow (r / 255, 2.2);
    g = Math.pow (g / 255, 2.2);
    b = Math.pow (b / 255, 2.2);

    return 0.212671*r + 0.715160*g + 0.072169*b;
};

creme.color.contrast = function(r, g, b, r2, g2, b2) {
    var luminance1 = creme.utils.luminance(r, g, b);
    var luminance2 = creme.utils.luminance(r2, g2, b2);
    return (Math.max(luminance1, luminance2) + 0.05) / (Math.min(luminance1, luminance2) + 0.05);
};

creme.color.maxContrastingColor = function(r, g, b) {
    var withWhite = creme.utils.contrast(r, g, b, 255, 255, 255);
    var withBlack = creme.utils.contrast(r, g, b, 0, 0, 0);

    if (withWhite > withBlack)
        return 'white';
    return 'black'; //TODO: ? 'white': 'black';
};
