/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2009-2022  Hybird

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

/* istanbul ignore next : compatibility with IE < 8.0 */
(function() {
    "use strict";

    if (!window['Event']) {
        window['Event'] = function() {};
    }

    function append(klass, name, method) {
        if (!klass.prototype[name]) {
            klass.prototype[name] = method;
        }
    };

    append(Event, 'stopPropagation', function() {
        this.cancelBubble = true;
    });

    append(Event, 'preventDefault', function() {
        this.returnValue = false;
    });

    if (!window['ResizeObserver']) {
        window['ResizeObserver'] = function() {};
    }

    append(ResizeObserver, 'observe', function() {});
    append(ResizeObserver, 'unobserve', function() {});
    append(ResizeObserver, 'disconnect', function() {});
}());
