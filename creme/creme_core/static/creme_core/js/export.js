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

/*
 * Requires : creme declaration
 */

(function($) {"use strict";

creme.exports = creme.exports || {};

creme.exports.exportAs = function(url, formats, argument_name) {
    var formats = !Object.isEmpty(formats) ? formats : [['', 'No backend found']];

    return creme.dialogs
                .choice(gettext("Select the export format"), {
                    title: gettext("Export"),
                    choices: formats.map(function(item) {return {value:item[0], label:item[1]}})
                })
                .onOk(function(event, data) {
                    if (argument_name === undefined) {
                        console.warn('creme.exports.exportAs(): URL as format string is deprecated ; use the the "argument_name" parameter instead.');
                        window.location.href = url.format(data);
                    } else {
                        window.location.href = url + '&' + argument_name + '=' + data;
                    }
                })
                .open();
};
}(jQuery));