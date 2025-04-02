/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2022-2025  Hybird

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

/* TODO: button to deselect all? */
/* TODO: input to search/filter in choices? */
/* TODO: use <select> instead ? */
creme.widget.OrderedListSelect = creme.widget.declare('ui-creme-ordered', {
    _create: function(element, options) {
        options = options || {};

        this._dataIdAttr = options.dataIdAttr || 'data-choice-id';
        this._notDraggableClass = options.notDraggableClass || 'not-draggable';

        this._targetInput = element.find('input.ordered-widget-value');
        this._choicesContainer = element.find('.ordered-widget-available-choices');
        this._selectionContainer = element.find('.ordered-widget-enabled-choices');

        this._setupItems(element);
        this._setupDragNDrop(element);

        element.on('dblclick', '.ordered-widget-choice', function(e) {
            e.preventDefault();
            this._moveItem($(e.target).closest('.ordered-widget-choice'));
        }.bind(this));

        element.on('click', '.ordered-widget-enabled-choices .deselect-choice', function(e) {
            e.preventDefault();
            this._moveItem($(e.target).closest('.ordered-widget-choice'));
        }.bind(this));

        element.addClass('widget-ready');
    },

    _setupItems: function(element) {
        var choices = this.choices(element).slice();
        var selected = this.selected(element);

        var availableItems = [];
        var selectedItems = [];

        selected.forEach(function(value) {
            var index = choices.findIndex(function(choice) {
                return choice.value === value;
            });

            if (index !== -1) {
                selectedItems.push(this._itemHtml(choices[index]));
                choices.splice(index, 1);
            }
        }.bind(this));

        choices.forEach(function(choice) {
            availableItems.push(this._itemHtml(choice));
        }.bind(this));

        this._choicesContainer.html(availableItems.join(''));
        this._selectionContainer.html(selectedItems.join(''));
    },

    _setupDragNDrop: function(element) {
        var groupName = element.attr('id');

        this._choicesSortable = new Sortable(this._choicesContainer.get(0), {
            group: {
                name: groupName,
                put: false
            },
            dataIdAttr: this._dataIdAttr,
            filter: '.' + this._notDraggableClass,
            sort: false
        });

        this._selectionSortable = new Sortable(this._selectionContainer.get(0), {
            group: groupName,
            dataIdAttr: this._dataIdAttr,
            filter: '.' + this._notDraggableClass,
            onSort: this._updateInput.bind(this)
        });
    },

    _updateInput: function(e) {
        this._targetInput.val(JSON.stringify(this._selectionSortable.toArray()));
    },

    selected: function(element) {
        var data = JSON.parse(this._targetInput.val());
        return Array.isArray(data) ? data : [];
    },

    choices: function(element) {
        if (Object.isNone(this._choices)) {
            var script = element.find('script[type$="/json"]');
            var choices = [];

            try {
                if (!Object.isEmpty(script)) {
                    var data = _.readJSONScriptText(script.get(0));
                    choices = Object.isEmpty(data) ? [] : JSON.parse(data);
                }
            } catch (e) {
                console.warn(e);
            }

            // We compute the order to use when a chosen element is deselected, to re-insert it among available elements.
            this._choices = choices.map(function(choice, index) {
                choice.initialOrder = index;
                return choice;
            });
        }

        return this._choices;
    },

    _itemHtml: function(choice) {
        return (
            '<div class="ordered-widget-choice ${notDraggable}" ${idAttr}="${value}" data-order="${order}" ${help}>' +
                '<span>${label}</span>' +
                '<button type="button" class="deselect-choice" ${buttonDisabled}>${buttonLabel}</button>' +
            '</div>'
        ).template({
            idAttr: this._dataIdAttr,
            value: choice.value,
            order: choice.initialOrder,
            help: choice.help ? 'title="${help}"'.template(choice) : '',
            label: choice.label,
            notDraggable: choice.disabled ? this._notDraggableClass : '',
            buttonDisabled: choice.disabled ? 'disabled' : '',
            buttonLabel: gettext('Deselect')
        });
    },

    _moveItem: function(item) {
        var container = item.parent('.ordered-widget-choices');
        var selected = container.hasClass('ordered-widget-enabled-choices');

        // Move to available choices
        if (selected) {
            var order = parseInt(item.data('order'));
            var target = this._choicesContainer.find('.ordered-widget-choice').filter(function() {
                return (order < parseInt($(this).data('order')));
            }).first().get(0);

            if (Object.isNone(target)) {
                this._choicesContainer.append(item);
            } else {
                $(target).before(item);
            }
        } else {  // Move to selected choices
            this._selectionContainer.append(item);
        }

        this._updateInput();
    }
});

}(jQuery));
