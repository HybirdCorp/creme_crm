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
creme.widget.SelectOrInputWidget = creme.widget.declare('ui-creme-union', {
    _create: function(element, options) {
        var handler = function() {

            // TODO: disabled input/select/... (beware: do not re-enable inputs which were already disabled => store state)
            //       VS intercept all the events in the container
            element.find('.union-sub_widget').each(function() {
                var sub_widget = $(this);
                sub_widget.find('.union-sub_widget_container').toggleClass('switch-on', sub_widget.find('.union-widget-switch').prop('checked'));
            });
        };

        handler(); // Initial state
        element.find('.union-widget-switch').on('change', handler);

        element.addClass('widget-ready');
    }
});

}(jQuery));
