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

(function($) {
"use strict";

creme.utils = creme.utils || {};

creme.utils.JSON = function() {};
creme.utils.JSON.prototype = {
    encode: function(data) {
        console.warn('creme.utils.JSON.encode is deprecated; Use JSON.stringify instead.');
        return JSON.stringify(data);
        /*
        if (window.JSON && window.JSON.stringify) {
            return window.JSON.stringify(data);
        }

        throw Error('not implemented !');
        */
    },

    isJSON: function(data) {
        console.warn('creme.utils.JSON.isJSON is deprecated; Use _.isJSON instead.');
        return _.isJSON(data);
        /*
        // Make sure the incoming data is actual JSON
        // Logic borrowed from http://json.org/json2.js
        return typeof data === 'string' &&
               (/^[\],:{}\s]*$/.test(data.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
                                         .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
                                         .replace(/(?:^|:|,)(?:\s*\[)+/g, "")));
        */
    },

    decode: function(data, defaults) {
        if (defaults !== undefined) {
            try {
                return this.decode(data);
            } catch (e) {
                return defaults;
            }
        }

        console.warn('creme.utils.JSON.decode is deprecated; Use _.cleanJSON instead.');

        if (typeof data !== "string" || !data) {
            throw Error('Invalid data type or empty string');
        }

        return JSON.parse(data);
        /*
        // Make sure leading/trailing whitespace is removed (IE can't handle it)
        data = (data || '').trim();

        try {
            if (window.JSON && window.JSON.parse) {
                return window.JSON.parse(data);
            }
        } catch (err) {
            throw Error('JSON parse error: ' + err);
        }

        var isvalid = this.isJSON(data);

        if (!isvalid) {
            throw Error('JSON parse error (fallback)');
        }

        try {
            // Try to use jQuery instead
            return $.parseJSON(data);
        } catch (err) {
            throw Error('JSON parse error (fallback): ' + err);
        }
        */
    }
};

/*
creme.utils.JSON.decoder = function(defaults) {
    var codec = new creme.utils.JSON();

    return function(data, value) {
        return codec.decode(data, value || defaults);
    };
};

creme.utils.JSON.encoder = function() {
    return new creme.utils.JSON().encode;
};
*/

creme.utils.JSON.clean = function(data, defaults) {
    console.warn('creme.utils.JSON.clean is deprecated; Use _.cleanJSON instead.');
    return _.isString(data) ? _.cleanJSON(data) || defaults : data;
    /*
    return Object.isString(data) ? new creme.utils.JSON().decode(data, defaults) : data;
    */
};

creme.utils.JSON.readScriptText = function(element, options) {
    console.warn('creme.utils.JSON.readScriptText is deprecated; Use _.readJSONScriptText instead.');
    element = $(element).first();
    options = Object.assign({
        ignoreEmpty: false
    }, options || {});

    // TODO : seems never used remove it ?
    if (element.length === 0) {
        if (!options.ignoreEmpty) {
            console.warn('No such JSON script element');
        }

        return '';
    }

    return _.readJSONScriptText(element.get(0));
    /*
    if (!element.is('script') || ['text/json', 'application/json'].indexOf(element.attr('type')) === -1) {
        console.warn('This element is not a JSON script', element);
        return '';
    }

    var startTag = '<!--';
    var endTag = '-->';

    var rawData = ($(element).text() || '').replace(/^[\s\n\r]+|[\s\n\r]+$/g, '');

    if (Object.isEmpty(rawData)) {
        return rawData;
    }

    if (rawData.startsWith(startTag) && rawData.endsWith(endTag)) {
        rawData = rawData.slice(startTag.length, rawData.length - endTag.length);
    } else {
        console.warn('Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript');
    }

    return rawData.trim().replace(/\\u005c/gi, '\\')
                         .replace(/\\u0026/gi, '&')
                         .replace(/\\u003c/gi, '<')
                         .replace(/\\u003e/gi, '>')
                         .replace(/\\u2028/gi, '\u2028')
                         .replace(/\\u2029/gi, '\u2029');
    */
};

}(jQuery));
