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
 * Requires : creme, jQuery, creme.utils
 */

creme.emails = {};

//creme.emails.confirmResend = function(message, ids, block_url) {
creme.emails.confirmResend = function(message, resend_url, ids, block_url) {
//    return creme.blocks.confirmPOSTQuery('/emails/mail/resend',
    return creme.blocks.confirmPOSTQuery(resend_url,
                                         {blockReloadUrl: block_url,
                                          messageOnSuccess: gettext('Process done'),
                                          confirm: message
                                         },
                                         {ids: ids}
                                        )
                       .start();
}

//creme.emails.resend = function(ids, block_url) {
creme.emails.resend = function(resend_url, ids, block_url) {
//    return creme.blocks.ajaxPOSTQuery('/emails/mail/resend',
    return creme.blocks.ajaxPOSTQuery(resend_url,
                                      {blockReloadUrl: block_url,
                                       messageOnSuccess: gettext('Process done')
                                      })
                       .data({ids: ids})
                       .start();
}

creme.emails.allowExternalImages = function(block_id) {
    var iframe = $('#' + block_id).find('iframe');
    iframe.attr('src', iframe.attr('src') + '?external_img=on');
}
