/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2017  Hybird

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
 * Requires : creme, jQuery, creme.blocks, creme.bricks
 */

(function($) {
"use strict";

creme.emails = {};

//creme.emails.confirmResend = function(message, ids, block_url) {
creme.emails.confirmResend = function(message, resend_url, ids, block_url) {
    console.warn('creme.emails.confirmResend() is deprecated ; use an action with the url "emails__resend_emails" instead.');
//    return creme.blocks.confirmPOSTQuery('/emails/mail/resend',
    return creme.blocks.confirmPOSTQuery(resend_url,
                                         {blockReloadUrl: block_url,
                                          messageOnSuccess: gettext('Process done'),
                                          confirm: message
                                         },
                                         {ids: ids}
                                        )
                       .start();
};

//creme.emails.resend = function(ids, block_url) {
creme.emails.resend = function(resend_url, ids, block_url) {
    console.warn('creme.emails.resend() is deprecated ; use an action with the url "emails__resend_emails" instead.');

//    return creme.blocks.ajaxPOSTQuery('/emails/mail/resend',
    return creme.blocks.ajaxPOSTQuery(resend_url,
                                      {blockReloadUrl: block_url,
                                       messageOnSuccess: gettext('Process done')
                                      })
                       .data({ids: ids})
                       .start();
};

creme.emails.allowExternalImages = function(block_id) {
    console.warn('creme.emails.allowExternalImages() is deprecated ; use the action "email-toggle-images" instead.');

    var iframe = $('#' + block_id).find('iframe');
    iframe.attr('src', iframe.attr('src') + '?external_img=on');
};


(function() {
    var emptySelectionAction = function(message) {
        return new creme.component.Action(function() {
            var self = this;
            creme.dialogs.warning(message)
                         .onClose(function() {self.fail();})
                         .open();
        });
    };

    var emailSyncActions = {
        _action_emailsync_link: function(url, options, data, e) {
            var values = $(data.selector).getValues();

            if (values.length === 0) {
                return emptySelectionAction(gettext('Please select at least one entity.'));
            }

            url += '?' + $.param({persist: 'id', ids: values, rtype: data.rtypes});

            return this._action_form(url, options, data, e);
        },

        _action_emailsync_action: function(url, options, data, e) {
            var values = $(data.selector).getValues();

            if (values.length === 0) {
                return emptySelectionAction(gettext('Nothing is selected.'));
            }

            return this._action_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
        },

        _action_emailsync_delete: function(url, options, data, e) {
            var values = $(data.selector).getValues();

            if (values.length === 0) {
                return emptySelectionAction(gettext('Nothing is selected.'));
            }

            return this._action_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values.join(',')}, e);
        },
    };

    $(document).on('brick-before-bind', '.brick.emails-emailsync-brick', function(e, brick, options) {
        $.extend(brick, emailSyncActions);
    });

    var emailActions = {
        _action_email_toggle_images: function(url, options, data, e) {
            var iframe = this._element.find('iframe[data-html-field]');
            var link = document.createElement('a'); link.href = iframe.attr('src');
            var visible = link.search.indexOf('external_img=on') !== -1;
            var url = link.pathname + (visible ? '' : '?external_img=on');
            var title = $(e.target).find('.brick-action-title');

            if (title.length) {
                title.text(visible ? data.inlabel : data.outlabel);
            } else {
                $(e.target).text(visible ? data.inlabel : data.outlabel);
            }

            iframe.attr('src', url);
        },
    }

    $(document).on('brick-before-bind', '.brick.emails-email-brick', function(e, brick, options) {
        $.extend(brick, emailActions);
    });
}());

}(jQuery));
