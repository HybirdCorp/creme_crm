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

creme.layout = creme.layout || {};

/* Component size change detection is already supported by any recent browsers with ResizeObserver
 * (see https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver/ResizeObserver)
 * TODO : Refactor Frame and deprecate this part.
 */

creme.layout.preferredSize = function(element, depth) {
    depth = depth || 1;

    var height = 0;
    var width = 0;

    $('> *', element).filter(':visible').each(function() {
        var position = $(this).position();

        if (depth > 1) {
            var size = creme.layout.preferredSize($(this), depth - 1);
            width = Math.max(width, size[0]);
            height = Math.max(height, size[1]);
        }

        width = Math.max(width, position.left + $(this).outerWidth(true));
        height = Math.max(height, position.top + $(this).outerHeight(true));
    });

    return [Math.round(width), Math.round(height)];
};
}(jQuery));
