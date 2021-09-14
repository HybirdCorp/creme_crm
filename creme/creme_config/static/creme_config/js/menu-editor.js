/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021  Hybird

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
creme.MenuEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        var self = this;
        var name = options.name || 'MISSING';

        this._element = element;
        this._input = $('<input type="hidden" name="${name}">'.template({name: name}));

        options = options || {};
        element.append(this._input);

        // TODO: error if not initial data ?
        if (options.initialSelector) {
            self._appendEntries(
                JSON.parse(creme.utils.JSON.readScriptText(element.find(options.initialSelector)))
            );
        }

        function onSortEventHandler(event) {
            self._updateValue();
        };

        this._entries = new Sortable(
            element.find('.menu-edit-entries').get(0),
            {
                group: element.attr('id'),
                animation: 150,
                onSort: onSortEventHandler
            }
        );

        // ----
        var regularChoices = [];
        if (options.regularChoicesSelector) {
            regularChoices = JSON.parse(
                creme.utils.JSON.readScriptText(element.find(options.regularChoicesSelector))
            );
        }

        var regularButton = element.find('.new-regular-entries');
        if (regularChoices) {
            regularButton.on('click', function(event) {
                self._regularEntriesDialog(regularChoices).open();
            });
        } else {
            regularButton.remove();
        }

        // --
        element.find('.new-extra-entry').each(function(i, node) {
            var button = $(node);

            button.on('click', function(event) {
                self._specialEntriesDialog(button).open();
            });
        });
    },

    _appendEntries: function(entriesInfo) {
        var self = this;
        var divs = this._element.find('.menu-edit-entries');

        entriesInfo.forEach(function(entryInfo) {
            // NB: text() performs an escaping so we're protected against malicious labels
            var entryDiv = $('<div>').attr('class', 'menu-edit-entry menu-edit-entry-' + entryInfo.value.id)
                                     .attr('data-value', JSON.stringify(entryInfo.value))
                                     .text(entryInfo.label);

            entryDiv.append(
                $(
                    '<button type="button">${label}</button>'.template({label: gettext('Delete')})
                ).on('click', function(e) {
                    e.preventDefault();
                    entryDiv.remove();
                    self._updateValue();
                })
            );
            divs.append(entryDiv);
        });

        this._updateValue();
    },

    _updateValue: function() {
        var values = $.map(this._element.find('.menu-edit-entry'), function(e) {
            return JSON.parse($(e).attr('data-value'));
        });

        this._input.val(JSON.stringify(values));
    },

    _regularEntriesDialog: function(choices) {
        var self = this;

        // TODO: var excluded = new Set( ... );
        // TODO: factorise ?
        var excluded = $.map(this._element.find('.menu-edit-entry'), function(e) {
            return JSON.parse($(e).attr('data-value')).id;
        });
        var options = choices.filter(function(c) {
            // return !excluded.has(c[0]);
            return excluded.indexOf(c[0]) === -1;
        }).map(function(c) {
            return '<option value="${value}">${label}</option>'.template({
                value: c[0],
                label: c[1]
            });
        });

        if (options.length === 0) {
            return new creme.dialog.ConfirmDialog(gettext('All menu entries are already used.'));
        } else {
            var html = (
                '<form class="menu-edit-regular-entries">' +
                    '<div class="help-text">${help}</div>' +
                    '<select name="entry_type" multiple>${choices}</select>' +
                    '<button class="ui-creme-dialog-action" type="submit">${label}</button>' +
                '</form>'
            ).template({
                label: gettext('Add entries'),
                help: gettext('Hold down “Control”, or “Command” on a Mac, to select more than one.'),
                choices: options.join('')
            });

            var formDialog = new creme.dialog.FormDialog({
                title: gettext('New entries'),

                fitFrame:   false,
                height: 400,
                width:  500,
                noValidate: true,
                html: $(html)
            });

            // All custom logic for buttons & widget is done BEFORE the frame-activated event
            formDialog.on('frame-activated', function() {
                this.button('send').on('click', function() {
                    var newEntries = [];
                    formDialog.form().find('[name="entry_type"] option:selected').each(function() {
                        var option = $(this);

                        newEntries.push({
                            label: option.text(),
                            value: {id: option.val()}
                        });
                    });

                    self._appendEntries(newEntries);

                    formDialog.close();
                });
            });

            return formDialog;
        }
    },

    _specialEntriesDialog: function(button) {
        var self = this;
        return new creme.dialog.FormDialog({
            url: button.attr('data-url')
        }).onFormSuccess(function(event, data) {
            if (data.isJSONOrObject()) {
                self._appendEntries(data.data());
            } else {
                console.log('_specialEntriesDialog expects JSON ; data received:', data);
            }
        });
    }
});

}(jQuery));
