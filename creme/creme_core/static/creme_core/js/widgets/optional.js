/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022  Hybird

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

/* TODO: unit test */
creme.widget.SelectOrInputWidget = creme.widget.declare('ui-creme-optional', {
    _create: function(element, options) {
        var checkBox = element.find('.optional-widget-trigger').first();
        var hiddable = element.find('.optional-widget-hiddable');

        // TODO: toggle between 2 CSS classes for better control of animation from CSS theme.
        var handler = function() {
            if (checkBox.prop('checked')) {
                hiddable.fadeIn();
            } else {
                hiddable.fadeOut();
            }
        };

        handler(); // Initial state
        checkBox.on('change', handler);

        element.addClass('widget-ready');
    }
});

}(jQuery));
