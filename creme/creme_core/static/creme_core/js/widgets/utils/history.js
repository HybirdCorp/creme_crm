/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017-2023  Hybird

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

    creme.history = creme.history || {};

    window.addEventListener("popstate", function(e) {
        if (e.state) {
            window.location.assign(e.state.url);
        }
    });

    creme.history.push = function(url, title) {
        title = title || document.title;
        window.history.pushState({title: title, url: url}, title, url);
    };

    creme.history.replace = function(url, title) {
        title = title || document.title;
        window.history.replaceState({title: title, url: url}, title, url);
    };
}(jQuery));
