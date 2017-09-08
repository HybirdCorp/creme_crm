/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2009-2017  Hybird

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

// HTMLDocument = $.assertIEVersions(7, 8, 9) ? function() {} : HTMLDocument;
// CSSStyleDeclaration = $.assertIEVersions(7) ? function() {} : CSSStyleDeclaration;

/* istanbul ignore next : compatibility with IE < 8.0 */
(function() {
    "use strict";

    if (!window['HTMLDocument']) {
        window['HTMLDocument'] = function () {};
    }

    if (!window['CSSStyleDeclaration']) {
        window['CSSStyleDeclaration'] = function () {};
    }

    function append(name, method) {
        if (!HTMLDocument.prototype[name]) {
            HTMLDocument.prototype[name] = method;
        }
    };

    append("createElementNS", function(namespace, name) {
        return this.createElement(name);
    });
}());
