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

function isJSON(data) {
    var output = null;

    try {
        output = _.isString(data) && data.length > 0 ? JSON.parse(data) : null;
    } catch (e) {}

    return output !== null;
    /*
    // Make sure the incoming data is actual JSON
    // Logic borrowed from http://json.org/json2.js
    return _.isString(data) &&
            (/^[\],:{}\s]*$/.test(data.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
                                        .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
                                        .replace(/(?:^|:|,)(?:\s*\[)+/g, "")));
    */
}

function cleanJSON(data, reviver) {
    try {
        if (_.isString(data) && data.length > 0) {
            return JSON.parse(data, reviver);
        }
    } catch (e) {}
}

function readJSONScriptText(element) {
    if (_.isString(element) && element.length > 0) {
        element = document.querySelector(element);
    }

    if (!_.isElement(element)) {
        console.warn('No such JSON script element');
        return '';
    }

    var isScript = (
        element.nodeName.toLowerCase() === 'script' &&
        ['text/json', 'application/json'].indexOf(element.getAttribute('type')) !== -1
    );

    if (!isScript) {
        console.warn('This element is not a JSON script', element);
        return '';
    }

    var startTag = '<!--';
    var endTag = '-->';
    var rawData = (element.text || '').replace(/^[\s\n\r]+|[\s\n\r]+$/g, '');  // trim spacing chars.

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
}

function cleanJSONScript(element, reviver) {
    return _.cleanJSON(_.readJSONScriptText(element), reviver);
}

_.mixin({
    isJSON: isJSON,
    readJSONScriptText: readJSONScriptText,
    cleanJSON: cleanJSON,
    cleanJSONScript: cleanJSONScript
});

}());
