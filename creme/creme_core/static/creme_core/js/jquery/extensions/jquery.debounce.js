/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

// deBouncer by hnldesign.nl
// based on code by Paul Irish and the original debouncing function from John Hann
// http://unscriptable.com/index.php/2009/03/20/debouncing-javascript-methods/
(function($) {
    $.debounce = function(func, threshold, execAsap) {
        var timeout;

        return function debounced() {
            var self = this
            var args = arguments;

            function delayed() {
                if (!execAsap)
                    func.apply(self, args);
                timeout = null;
            }

            if (timeout)
                clearTimeout(timeout);
            else if (execAsap)
                func.apply(self, args);

            timeout = setTimeout(delayed, threshold || interval);
        };
    };

    $.debounceEvent = function(name, event, interval) {
        return function(fn) {return fn ? this.bind(event, $.debounce(fn)) : this.trigger(name);};
    };

    $.fn.resizepause = $.debounceEvent('resizepause', 'resize', 100);
    $.fn.movepause = $.debounceEvent('movepause', 'move', 100);
    $.fn.scrollpause = $.debounceEvent('scrollpause', 'scroll', 100);
})($);
