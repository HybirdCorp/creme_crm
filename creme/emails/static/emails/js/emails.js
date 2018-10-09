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

}(jQuery));
