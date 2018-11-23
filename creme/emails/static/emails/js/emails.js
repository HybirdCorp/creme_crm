/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

var emailSyncActions = {
    'emailsync-link': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Please select at least one entity.'));
        }

        url += '?' + $.param({persist: 'id', ids: values, rtype: data.rtypes});

        return this._build_form_refresh(url, options, data, e);
    },

    'emailsync-action': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
    },

    'emailsync-delete': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values.join(',')}, e);
    }
};

$(document).on('brick-setup-actions', '.brick.emails-emailsync-brick', function(e, brick, actions) {
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

        dialog.onFormSuccess(function(event, data) {
                    var deps = ['creme_core.relation'].concat(options.rtypes.map(function(rtype) {
                                                                                     return 'creme_core.relation.' + rtype;
                                                                                 }));

                    new creme.bricks.BricksReloader().dependencies(deps).action().start();
                    self.done();
               })
               .onClose(function() {
                   self.cancel();
               })
               .open({width: 800});
    }
});

$(document).on('hatmenubar-setup-actions', '.ui-creme-hatmenubar', function(e, actions) {
    actions.register('emails-hatmenubar-linkto', function(url, options, data, e) {
        return new creme.emails.LinkEMailToAction({
            url: url,
            rtypes: data.rtypes,
            ids: data.ids
        });
    });
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
        var selection = creme.lv_widget.selectedLines(list);

        if (Array.isArray(options.selection)) {
            selection = selection.concat(options.selection);
        }

        if (selection.length < 1) {
            creme.dialogs.warning(gettext("Please select at least one e-mail."))
                         .onClose(function() {
                             self.cancel();
                          })
                         .open();
        } else {
            var query = creme.utils.confirmPOSTQuery(options.url, {warnOnFail: false, dataType: 'json'}, {ids: selection.join(',')});
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
