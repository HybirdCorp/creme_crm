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

var DJANGO_INTL_CODES = {
    'fr': 'fr-FR',
    'en': 'en-US'
};

function getDjangoLanguageCode() {
    var code = window.LANGUAGE_CODE || getBrowserLanguageCode();
    return DJANGO_INTL_CODES[code] || code;
}

function getBrowserLanguageCode() {
    return (window.navigator || {}).language || 'en-US';
}

_.mixin({
    djangoLanguageCode: getDjangoLanguageCode,
    languageCode: getBrowserLanguageCode
});

}());
