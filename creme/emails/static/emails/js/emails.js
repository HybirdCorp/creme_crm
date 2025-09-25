/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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
 * Requires : creme, jQuery, creme.bricks
 */

(function($) {
"use strict";

creme.emails = {};

creme.emails.LinkEMailToAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = $.extend({}, this._options, options || {});

        var self = this;
        var formData = {
            ids: options.ids,
            rtype: options.rtypes
        };

        var dialog = creme.dialogs.form(options.url, {submitData: formData}, formData);

        // TODO: something like <dialog.onFormSuccess(self._refreshBrick.bind(self)).onClose ...>
        dialog.onFormSuccess(function(event, data) {
            var deps = ['creme_core.relation'].concat(
                options.rtypes.map(function(rtype) {
                    return 'creme_core.relation.' + rtype;
                })
            );

            new creme.bricks.BricksReloader().dependencies(deps).action().start();
            self.done();
        }).onClose(function() {
            self.cancel();
        }).open({width: 1024});
    }
});

$(document).on('brick-setup-actions', '.creme_core-buttons-brick', function(e, brick, actions) {
    actions.register('emails-hatmenubar-linkto', function(url, options, data, e) {
        return new creme.emails.LinkEMailToAction({
            url: url,
            rtypes: data.rtypes,
            ids: data.ids
        });
    });
});

// TODO: really useful?
var _emailSyncSelection = function(registry, data) {
    if (Object.isEmpty(data.id)) {
        return registry._selectedRowValues().filter(Object.isNotEmpty);
    } else {
        return [data.id];
    }
};

creme.emails.MultiSelectedAction = creme.component.Action.sub({
    _init_: function(brick, ids, options) {
        options = $.extend({
             successMessageBuilder: function(count) {
                 return '%d email(s) have been processed.'.format(count);
             },
             failMessageBuilder: function(count) {
                 return '%d email(s) cannot be processed.'.format(count);
             }
        }, options || {});

        this._super_(creme.component.Action, '_init_', this._run, options);
        this._brick = brick;
        this._ids = ids;

        Assert.not(Object.isEmpty(options.url), "'url' option is required");
        this._url = options.url;

        this._successMessageBuilder = options.successMessageBuilder;
        this._failMessageBuilder = options.failMessageBuilder;
    },

    _onMultiFail: function(event, data, response) {
        var message = gettext('Some errors occurred.');
        var header = creme.ajax.localizedErrorMessage(response.status);

        if (!Object.isEmpty(data) && _.isJSON(data)) {
            var results = JSON.parse(data);
            var removedCount = results.count - results.errors.length;

            if (removedCount > 0) {
                header = this._successMessageBuilder(removedCount);
            }

            if (results.errors) {
                header += ' - ' + this._failMessageBuilder(results.errors.length);
            }

            message = '<ul>' +
                      results.errors.map(function(item) {
                           return '<li>' + item + '</li>';
                      }).join('') +
                      '</ul>';
        }

        var brick = this._brick;
        creme.dialogs.warning(message, {header: header})
                     .onClose(function() { brick.refresh(); })
                     .open();
    },

    _run: function(options) {
        // options = $.extend({}, this.options(), options || {});
        var self = this;

        var query = creme.utils.ajaxQuery(self._url, {action: 'POST', confirm: true, warnOnFail: false}, {ids: self._ids.join(',')});
        query.onDone(function() { self._brick.refresh(); })
             .onFail(this._onMultiFail.bind(this))
             .start();
    }
});

var emailSyncActions = {
    // TODO: factorise !!
    'emailsync-accept': function(url, options, data, e) {
        var id = data.ids;

        if (!id) {
            return this._warningAction(gettext('No email is selected.'));
        }

        return new creme.emails.MultiSelectedAction(
            this._brick, [id],
            {
                url: url,
                successMessageBuilder: function(count) {
                    return ngettext('%d email has been synchronised',
                                    '%d emails have been synchronised',
                                    count).format(count);
                },
                failMessageBuilder: function(count) {
                    return ngettext('%d email cannot be synchronised.',
                                    '%d emails cannot be synchronised.',
                                    count).format(count);
                }
            }
        );
    },

    'emailsync-accept-multi': function(url, options, data, e) {
        var ids = _emailSyncSelection(this, data);

        if (Object.isEmpty(ids)) {
            return this._warningAction(gettext('No email is selected.'));
        }

        return new creme.emails.MultiSelectedAction(
            this._brick, ids,
            {
                url: url,
                successMessageBuilder: function(count) {
                    return ngettext('%d email has been synchronised',
                                    '%d emails have been synchronised',
                                    count).format(count);
                },
                failMessageBuilder: function(count) {
                    return ngettext('%d email cannot be synchronised.',
                                    '%d emails cannot be synchronised.',
                                    count).format(count);
                }
            }
        );
    },

    // TODO: factorise
    'emailsync-delete': function(url, options, data, e) {
        var id = data.ids;

        if (!id) {
            return this._warningAction(gettext('No email is selected.'));
        }

        return new creme.emails.MultiSelectedAction(
            this._brick, [id],
            {
                url: url,
                successMessageBuilder: function(count) {
                    return ngettext('%d email has been deleted',
                                    '%d emails have been deleted',
                                    count).format(count);
                },
                failMessageBuilder: function(count) {
                    return ngettext('%d email cannot be deleted.',
                                    '%d emails cannot be deleted.',
                                    count).format(count);
                }
            }
        );
    },

    'emailsync-delete-multi': function(url, options, data, e) {
        var ids = _emailSyncSelection(this, data);

        if (Object.isEmpty(ids)) {
            return this._warningAction(gettext('No email is selected.'));
        }

        return new creme.emails.MultiSelectedAction(
            this._brick, ids,
            {
                url: url,
                successMessageBuilder: function(count) {
                    return ngettext('%d email has been deleted',
                                    '%d emails have been deleted',
                                    count).format(count);
                },
                failMessageBuilder: function(count) {
                    return ngettext('%d email cannot be deleted.',
                                    '%d emails cannot be deleted.',
                                    count).format(count);
                }
            }
        );
    }
};

$(document).on('brick-setup-actions', '.brick.emails-emails_to_sync-brick', function(e, brick, actions) {
    actions.registerAll(emailSyncActions);
});

var emailActions = {
    'email-toggle-images': function(url, options, data, e) {
        var iframe = this._brick.element().find('iframe[data-html-field]');
        var link = document.createElement('a'); link.href = iframe.attr('src');
        var visible = link.search.indexOf('external_img=on') !== -1;
        var nexturl = link.pathname + (visible ? '' : '?external_img=on');
        var title = $(e.target).find('.brick-action-title');

        if (title.length) {
            title.text(visible ? data.inlabel : data.outlabel);
        } else {
            $(e.target).text(visible ? data.inlabel : data.outlabel);
        }

        iframe.attr('src', nexturl);
    }
};

$(document).on('brick-setup-actions', '.brick.emails-email-brick', function(e, brick, actions) {
    actions.registerAll(emailActions);
});

creme.emails.ResendEMailsAction = creme.component.Action.sub({
    _init_: function(list, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._list = list;
    },

    _onResendFail: function(event, error, data) {
        var self = this;
        var list = this._list;

        var message = Object.isType(error, 'string') ? error : (error.message || gettext("Error"));
        var header = creme.ajax.localizedErrorMessage(data);

        creme.dialogs.warning(message, {header: header})
                     .onClose(function() {
                          list.reload();
                          self.fail();
                      })
                     .open();
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var list = this._list;
        var selection = list.selectedRows();

        if (Array.isArray(options.selection)) {
            selection = _.unique(selection.concat(options.selection));
        }

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one email."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var query = creme.utils.ajaxQuery(options.url, {action: 'POST', confirm: true, warnOnFail: false}, {ids: selection.join(',')});
            query.onFail(this._onResendFail.bind(this))
                 .onCancel(function(event, data) {
                     self.cancel();
                  })
                 .onDone(function(event, data) {
                     list.reload();
                     self.done();
                  })
                 .start();
        }
    }
});

$(document).on('listview-setup-actions', '.ui-creme-listview', function(e, actions) {
    actions.register('email-resend-selection', function(url, options, data, e) {
        return new creme.emails.ResendEMailsAction(this._list, {url: url});
    });

    actions.register('email-resend', function(url, options, data, e) {
        return new creme.emails.ResendEMailsAction(this._list, {url: url, selection: options.selection});
    });
});

}(jQuery));
