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

creme.BricksConfigEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = this.options = options || {};
        this.element = element;
        this.groups = {
            available: element.find('.widget-choices.widget-available-choices'),
            top: element.find('.widget-choices.widget-enabled-top-choices'),
            right: element.find('.widget-choices.widget-enabled-right-choices'),
            left: element.find('.widget-choices.widget-enabled-left-choices'),
            bottom: element.find('.widget-choices.widget-enabled-bottom-choices')
        };

        if (options.choices) {
            this._populateChoices(JSON.parse(
                $(options.choices).text() || '[]'
            ));
        }

        this._initializeWidget({
            group: element.attr('id'),
            dataIdAttr: "data-choice-id",
            onSort: this._onSort.bind(this)
        });
    },

    _onSort: function (event) {
        if (this.options.targetInput) {
            this.options.targetInput.val(this._serializeWidget());
        }
    },

    _buildButtonChoice: function (choice) {
        return $((
            '<div class="widget-choice" data-choice-id="${value}" title="${description}">' +
                '${name}' +
            '</div>'
        ).template($.extend({
            description: ''
        }, choice)));
    },

    _populateChoices: function(choices) {
        choices.forEach(
            function (choice) {
                var choiceGroup = this.groups[choice.orientation ? choice.orientation : "available"];
                choiceGroup.append(this._buildButtonChoice(choice));
            }.bind(this)
        );
    },

    _serializeWidget: function () {
        return JSON.stringify({
            top: this.widgets.top.toArray(),
            right: this.widgets.right.toArray(),
            left: this.widgets.left.toArray(),
            bottom: this.widgets.bottom.toArray()
        });
    },

    _initializeWidget: function (options) {
        this.widgets = {
            available: new Sortable(this.groups.available[0], $.extend({sort: false}, options)),
            top: new Sortable(this.groups.top[0], options),
            right: new Sortable(this.groups.right[0], options),
            left: new Sortable(this.groups.left[0], options),
            bottom: new Sortable(this.groups.bottom[0], options)
        };
    }

});

}(jQuery));
