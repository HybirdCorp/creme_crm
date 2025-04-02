/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2021-2025  Hybird

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

creme.MenuEditor = creme.component.Component.sub({
    _init_: function(element, options) {
        options = options || {};

        var self = this;
        var name = options.name || 'MISSING';

        this._element = element;
        this._input = $('<input type="hidden" name="${name}">'.template({name: name}));

        element.append(this._input);

        Assert.not(Object.isEmpty(options.initialSelector), 'MenuEditor missing options.initialSelector');

        this._appendEntries(
            JSON.parse(_.readJSONScriptText(element.find(options.initialSelector).get(0)))
        );

        this._sortable = new Sortable(
            element.find('.menu-edit-entries').get(0), {
                group: element.attr('id'),
                animation: 150,
                onSort: this._onSort.bind(this)
            }
        );

        // ----
        var regularChoices = [];
        if (Object.isNotEmpty(options.regularChoicesSelector)) {
            regularChoices = JSON.parse(
                _.readJSONScriptText(element.find(options.regularChoicesSelector).get(0))
            );
        }

        if (Object.isNotEmpty(regularChoices)) {
            element.on('click', '.new-regular-entries', function(event) {
                self._regularEntriesDialog(regularChoices).open();
            });
        } else {
            element.find('.new-regular-entries').remove();
        }

        element.on('click', '.new-extra-entry', function(event) {
            self._specialEntriesDialog($(this)).open();
        });

        element.on('click', '.menu-edit-entry button', function(e) {
            e.preventDefault();
            $(this).parent('.menu-edit-entry:first').remove();
            self._onSort();
        });
    },

    _appendEntries: function(entries) {
        var divs = this._element.find('.menu-edit-entries');
        var html = entries.map(function(entry) {
            var res = (
                '<div class="menu-edit-entry menu-edit-entry-${id}" data-value="${value}">' +
                    '<span>${label}</span>' +
                    '<button type="button">${delete_label}</button>' +
                '</div>'
            ).template({
                id: entry.value.id,
                value: JSON.stringify(entry.value).escapeHTML(),
                label: entry.label.escapeHTML(),
                delete_label: gettext('Delete')
            });
            return res;
        }).join('');

        divs.append(html);
        this._onSort();
    },

    _onSort: function(event) {
        this._input.val(JSON.stringify(this.entries()));
    },

    value: function() {
        return JSON.parse(this._input.val());
    },

    entries: function() {
        return this._element.find('.menu-edit-entry').map(function() {
            return $(this).data('value');
        }).get();
    },

    _regularEntriesDialog: function(choices) {
        var self = this;

        // TODO: var excluded = new Set( ... );
        var excluded = this.entries().map(function(e) { return e.id; });

        var options = choices.filter(function(c) {
            return excluded.indexOf(c[0]) === -1;
        }).map(function(c) {
            return '<option value="${0}">${1}</option>'.template(c);
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
            url: button.data('url')
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
