/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020-2021  Hybird

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

function __buildButtonChoice(choice) {
    return $('<span>').attr('class', 'menu_button')
                      .attr('title', choice.description)
                      .text(choice.label)
                      .append(
                          $('<input>').attr('type', 'hidden')
                                      .attr('name', choice.name)
                                      .val(choice.value)
                                      .prop('disabled', !choice.selected)
                      );
}

function __buildWidget(widget, choices) {
    choices.forEach(
        function (choice) {
            if (choice.selected) {
                widget.find(".widget-selected .widget-container").append(
                    __buildButtonChoice(choice)
                );
            } else {
                widget.find(".widget-available .widget-container").append(
                    __buildButtonChoice(choice)
                );
            }
        }
    );
}

creme.ButtonMenuEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = options || {};

        if (options.optionsId) {
            __buildWidget(element, JSON.parse(
                $('#${optionsId}'.template(options)).text() || '[]'
            ));
        }

        function onSortEventHandler(event) {
            element.find(".widget-available input").prop("disabled", true);
            element.find(".widget-selected input").prop("disabled", false);
        };

        var groupName = element.attr("id");

        this._availableList = new Sortable(
            element.find(".widget-available .widget-container").get(0), {
                group: groupName,
                animation: 150,
                sort: false,
                onSort: onSortEventHandler
            });

        this._selectedList = new Sortable(
            element.find(".widget-selected .widget-container").get(0), {
                group: groupName,
                animation: 150,
                onSort: onSortEventHandler
            });
    }
});

}(jQuery));
