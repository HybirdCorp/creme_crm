/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2025  Hybird

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

var PATTERN = /\$\{([\w\d\\.^\\s]+)\}/g;

function literal(text) {
    // return a template literal closure with extra info for tags & completion
    // eslint-disable-next-line
    var literal = new Function('params', `return \`${this}\`;`);

    Object.defineProperty(literal, "tags", {
        value: Array.from(new Set(text.match(PATTERN) || [])),
        writable: false
    });

    function validate(params) {
        try {
            literal(params);
            return true;
        } catch (e) {
            return false;
        }
    }

    Object.defineProperty(literal, "validate", {
        value: validate,
        writable: false
    });

    return literal;
}

_.mixin({
    literal: literal
});

}());
