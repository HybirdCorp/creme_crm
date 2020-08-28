/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020  Hybird

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

(function($) {
"use strict";

/* globals BrowserVersion */

window.BrowserVersion = {
    match: function(pattern, version) {
        var versionParts = version.split('.').map(parseInt);
        var matches = pattern.match(/(==|<|>|<=|>=)?([0-9]+)/);

        if (!(matches && matches.length === 3)) {
            return false;
        }

        var operator = matches[1] || '==';
        var value = parseInt(matches[2]) || 0;

        switch (operator) {
            case '==': return versionParts[0] === value;
            case '<=': return versionParts[0] <= value;
            case '>=': return versionParts[0] >= value;
            case '<': return versionParts[0] < value;
            case '>': return versionParts[0] > value;
        }

        return false;
    },
    isIE: function(pattern) {
        return window.navigator.appVersion.match(/MSIE ([0-9\.]+)/);
    },
    isChrome: function(pattern) {
        // headless chrome does not have window.chrome defined
        // (see https://github.com/ChromeDevTools/devtools-protocol/issues/83)
        if (!!window.chrome || /HeadlessChrome/.test(window.navigator.userAgent)) {
            if (pattern) {
                var parts = window.navigator.userAgent.match(/Chrom(?:e|ium)\/([0-9\.]+)/);
                return parts && parts.length === 2 ? BrowserVersion.match(pattern, parts[1]) : false;
            } else {
                return true;
            }
        }
    },
    isHeadless: function() {
        return Object.isNone(window.navigator.webdriver) === false;
    },
    isFirefox: function(pattern) {
        if ('MozAppearance' in document.documentElement.style) {
            if (pattern) {
                var parts = window.navigator.userAgent.match(/(?:Firefox)\/([0-9\.]+)/);
                return parts && parts.length === 2 ? BrowserVersion.match(pattern, parts[1]) : false;
            } else {
                return true;
            }
        }
    }
};

}(jQuery));
