/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2020  Hybird

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

// TODO : move this creme_core
creme.persons.copyTo = function (source, target) {
    source = Object.isString(source) ? $('#' + source) : $(source);
    target = Object.isString(target) ? $('#' + target) : $(target);

    source.find('input, textarea, select').each(function() {
        target.find('[name="' + $(this).attr('name') + '"]').val($(this).val());
    });

    /*
    if ($from.size() > 0 && $to.size() > 0) {
        var $to_fill = $to.find('input, textarea, select');

        // TODO: use ':input' selector ??
        $from.find('input, textarea, select').each(function(ind) {
            $($to_fill[ind]).val($(this).val());
        });
    }
    */
};

// creme.persons.become = function(url, organisations) {
//    if (Object.isEmpty(organisations)) {
//        return;
//    }
//
//    if (organisations && organisations.length > 1) {
//        creme.dialogs.choice(gettext('Select the concerned organisation.'),
//                             {choices: organisations, title: gettext('Organisation')})
//                     .onOk(function(event, orga_id) {
//                          creme.utils.ajaxQuery(url, {action: 'post', reloadOnSuccess: true, warnOnFail: true}, {id: orga_id}).start();
//                      })
//                     .open();
//    } else {
//        creme.utils.ajaxQuery(url, {action: 'post', reloadOnSuccess: true, warnOnFail: true}, {id: organisations[0].value}).start();
//    }
// };

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

        return action.onDone(function() {
            creme.utils.reload();
        });
    }
};

$(document).on('hatmenubar-setup-actions', '.ui-creme-hatmenubar', function(e, actions) {
    actions.registerAll(hatmenubarActions);
});

}(jQuery));
