/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2026  Hybird

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

/* globals BrowserVersion process self */

window.BrowserVersion = {
    match: function(pattern, version) {
        var versionParts = (version || '').split('.').map(parseInt);
        var matches = pattern.match(/^(==|<|>|<=|>=)?([0-9]+)$/);

        if (!(matches && matches.length === 3)) {
            return false;
        }

        var operator = matches[1] || '==';
        var value = parseInt(matches[2]);

        switch (operator) {
            case '==': return versionParts[0] === value;
            case '<=': return versionParts[0] <= value;
            case '>=': return versionParts[0] >= value;
            case '<': return versionParts[0] < value;
            case '>': return versionParts[0] > value;
        }
    },

    isIE: function(pattern) {
        if (typeof window !== 'undefined') {
            var parts = ((window.navigator || {}).appVersion || '').match(/MSIE ([0-9\.]+)/);

            if (!(parts && parts.length === 2)) {
                return false;
            }

            return pattern ? BrowserVersion.match(pattern, parts[1]) : true;
        }

        return false;
    },

    isChrome: function(pattern) {
        if (typeof window !== 'undefined') {
            var userAgent = (window.navigator || {}).userAgent || '';

            // headless chrome does not have window.chrome defined
            // (see https://github.com/ChromeDevTools/devtools-protocol/issues/83)
            if (!!window.chrome || /HeadlessChrome/.test(userAgent)) {
                var parts = userAgent.match(/Chrom(?:e|ium)\/([0-9\.]+)/);

                if (!(parts && parts.length === 2)) {
                    return false;
                }

                return pattern ? BrowserVersion.match(pattern, parts[1]) : true;
            }
        }

        return false;
    },

    isHeadless: function() {
        if (typeof window !== 'undefined') {
            var userAgent = window.navigator.userAgent || '';
            return (/HeadlessChrome/.test(userAgent) || !!window.navigator.webdriver);
        }

        return false;
    },

    isFirefox: function(pattern) {
        if (typeof window !== 'undefined') {
            var userAgent = window.navigator.userAgent || '';

            if ('MozAppearance' in document.documentElement.style) {
                var parts = userAgent.match(/(?:Firefox)\/([0-9\.]+)/);

                if (!(parts && parts.length === 2)) {
                    return false;
                }

                return pattern ? BrowserVersion.match(pattern, parts[1]) : true;
            }
        }

        return false;
    },

    isJSDom: function() {
        if (typeof window !== 'undefined') {
            return window.name === 'nodejs';
        } else if (typeof navigator !== 'undefined') {
            return (
                navigator.userAgent.includes("Node.js") ||
                navigator.userAgent.includes("jsdom")
            );
        }
    },

    isWebWorker: function() {
        return (
            typeof self === "object" &&
            self.constructor &&
            self.constructor.name === "DedicatedWorkerGlobalScope"
        );
    },

    isNode: function() {
        return (
            typeof process !== "undefined" &&
            process.versions !== null &&
            process.versions.node !== null
        );
    }
};

}());
