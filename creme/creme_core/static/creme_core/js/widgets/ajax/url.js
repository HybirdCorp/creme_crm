/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018-2025  Hybird

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
/* globals RelativeURL */

(function() {
"use strict";

creme.ajax = creme.ajax || {};

creme.ajax.URL = RelativeURL;

creme.ajax.parseUrl = function(url) {
    console.warn('creme.ajax.parseUrl() is deprecated; Use _.urlAsDict() instead');
    return _.urlAsDict(url);
};

creme.ajax.param = function(data) {
    console.warn('creme.ajax.param() is deprecated; Use _.encodeURLSearch() instead');
    return _.encodeURLSearch(data);
};

creme.ajax.decodeSearchData = function(search) {
    console.warn('creme.ajax.decodeSearchData() is deprecated; Use _.decodeURLSearchData() instead');
    return _.decodeURLSearchData(search);
};

}());
