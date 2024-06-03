/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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

/*
 * Requires : jQuery, creme.utils, creme.dialogs
 */

(function($) {
"use strict";

creme.persons = creme.persons || {};

creme.persons.copyAddressInputs = function(source_prefix, target_prefix, source_root, target_root) {
    if (target_root === undefined) {
        target_root = source_root;
    }

    source_root.find('input, textarea, select').filter('[name|=' + source_prefix + ']').each(function() {
        target_root.find('input, textarea, select').filter(
            '[name=' + $(this).attr('name').replace(source_prefix, target_prefix) + ']'
        ).val($(this).val());
    });
};

creme.persons.BecomeAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _saveRelationship: function(options, selected) {
        var self = this;
        var url = options.url;

        if (Object.isEmpty(url)) {
            url = $('body').attr('data-save-relations-url');
        }

        creme.utils.ajaxQuery(url, {
                        action: 'post',
                        warnOnFail: true
                    }, {
                        subject_id: options.subject,
                        predicate_id: options.rtype,
                        entities: selected
                    })
                   .onFail(function(event, message) { self.fail(message); })
                   .onDone(function() { self.done(); })
                   .start();
    },

    _run: function(options) {
        options = $.extend({}, this._options, options || {});

        var self = this;
        var organisations = options.organisations || [];

        if (Object.isEmpty(organisations)) {
            this.cancel();
            return;
        }

        if (organisations.length > 1) {
            creme.dialogs.choice(gettext('Select the concerned organisation.'), {
                               required: true,
                               choices: organisations,
                               title: gettext('Organisation')
                           })
                          .onOk(function(event, selected) {
                               self._saveRelationship(options, selected);
                           })
                          .onClose(function(event, data) {
                               self.cancel();
                           })
                          .open();
        } else {
            this._saveRelationship(options, organisations[0].value);
        }
    }
});

var hatmenubarActions = {
    'persons-hatmenubar-become': function(url, options, data, e) {
        var action = new creme.persons.BecomeAction({
            url: url,
            subject: data.subject_id,
            rtype: data.rtype_id,
            organisations: data.organisations
        });

        return action.onDone(this._refreshBrick.bind(this));
    }
};

$(document).on('brick-setup-actions', '.creme_core-buttons-brick', function(e, brick, actions) {
    actions.registerAll(hatmenubarActions);
});

}(jQuery));
