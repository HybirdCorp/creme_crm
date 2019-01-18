/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

(function($) {
"use strict";

creme.exports = creme.exports || {};

creme.exports.exportAs = function(url, formats, fieldname) {
    formats = formats || [['', 'No backend found']];

    return creme.dialogs.choice(gettext("Select the export format"), {
                             title: gettext("Export"),
                             choices: formats.map(function(item) {
                                 return {value: item[0], label: item[1]};
                             }),
                             required: true
                         })
                        .onOk(function(event, data) {
                            var args = {};
                            args[fieldname] = data;
                            creme.utils.goTo(url, args);
                         })
                        .open();
};
}(jQuery));
