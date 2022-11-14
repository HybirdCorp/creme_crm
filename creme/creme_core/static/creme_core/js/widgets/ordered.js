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
/* TODO: button to deselect all? */
/* TODO: input to search/filter in choices? */
creme.widget.SelectOrInputWidget = creme.widget.declare('ui-creme-ordered', {
    _create: function(element, options) {
        this._dataIdAttr = options['dataIdAttr'] || 'data-choice-id';
        this._notDraggableClass = options['notDraggableClass'] || 'not-draggable';

        this._targetInput = element.find('.ordered-widget-value');
        this._availableContainer = element.find('.ordered-widget-available-choices');
        this._enabledContainer = element.find('.ordered-widget-enabled-choices');

        var choices = JSON.parse(creme.utils.JSON.readScriptText(element.find('.ordered-widget-choices')));

        // We compute the order to use when a chosen element is deselected, to re-insert it among available elements.
        choices.forEach(function(choice, index) {
            choice.originalOrder = index;
        });

        var selected = JSON.parse(this._targetInput.val());
        if (!Array.isArray(selected)) {
            throw new Error('SelectOrInputWidget: invalid selected values', selected);
        }

        selected.forEach(
            function(selected_id) {
                var index = choices.findIndex(function(choice) {
                    return (choice.value === selected_id);
                });

                this._enabledContainer.append(this._asEnabledEntry(this._buildEntry(choices[index])));
                choices.splice(index, 1);  // We remove the choice from the available ones.
            }.bind(this)
        );
        choices.forEach(
            function(choice) {
                this._availableContainer.append(this._buildEntry(choice));
            }.bind(this)
        );

        var groupName = element.attr('id');

        this._availableChoices = new Sortable(this._availableContainer.get(0), {
            group: {
                name: groupName,
                put: false
            },
            dataIdAttr: this._dataIdAttr,
            filter: '.' + this._notDraggableClass,
            sort: false
        });
        this._enabledChoices = new Sortable(this._enabledContainer.get(0), {
            group: groupName,
            dataIdAttr: this._dataIdAttr,
            filter: '.' + this._notDraggableClass,
            onSort: this._updateValue.bind(this),
            onAdd: function(event) { this._asEnabledEntry($(event.item)); }.bind(this)
        });

        element.addClass('widget-ready');
    },

    _buildEntry: function(choice) {
        var choiceClass = 'ordered-widget-choice';

        var entry = $('<div>').attr('class', choiceClass)
                              .attr(this._dataIdAttr, choice.value)
                              .attr('data-order', choice.originalOrder)
                              .attr('title', choice.help)
                              .append('<span>' + choice.label + '</span>');

        if (choice.disabled) {
            entry.addClass(this._notDraggableClass);
        } else {
            entry.dblclick(function(e) {
                this._transferChosen($(e.target).closest('.' + choiceClass));
            }.bind(this));
        }

        return entry;
    },

    _updateValue: function() {
        this._targetInput.val(JSON.stringify(this._enabledChoices.toArray()));
    },

    _asAvailableEntry: function(entryDiv) {
        entryDiv.find('button.deselect-choice').remove();

        return entryDiv;
    },

    _asEnabledEntry: function(entryDiv) {
        var deselectButton = $(
            '<button type="button" class="deselect-choice">${label}</button>'.template({
                label: gettext('Deselect')
            })
        );

        if (entryDiv.hasClass(this._notDraggableClass)) {
            // NB: we add the button to facilitate the layout, but we disable it (the CSS will hide it wink wink).
            deselectButton.prop('disabled', true);
        } else {
            deselectButton.on('click', function(e) {
                e.preventDefault();
                this._transferChosen(entryDiv);
            }.bind(this));
        }

        entryDiv.append(deselectButton);

        return entryDiv;
    },

    _transferChosen: function(entryDiv) {
        var parent = entryDiv.parent('.ordered-widget-choices');

        // Detach from its parent but keep the event handlers (double-click...)
        entryDiv.detach();

        if (parent.hasClass('ordered-widget-enabled-choices')) {
            var order = parseInt(entryDiv.attr('data-order'));
            var elementAfter = null;

            entryDiv = this._asAvailableEntry(entryDiv);

            this._availableContainer.children().each(function(index, element) {
                if (order < parseInt($(element).attr('data-order'))) {
                    elementAfter = element;
                    return false;
                }
            });

            if (elementAfter === null) {
                this._availableContainer.append(entryDiv);
            } else {
                $(elementAfter).before(entryDiv);
            }
        } else {
            this._enabledContainer.append(this._asEnabledEntry(entryDiv));
        }

        this._updateValue();
    }
});

}(jQuery));
