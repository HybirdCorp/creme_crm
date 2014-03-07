/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2014  Hybird

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

// creme.emails._processDone = function(cb) {
//     creme.dialogs.html('<p>%s</p>'.format(gettext('Process done'))).open();
//     if ($.isFunction(cb)) cb();
// }

// creme.emails.mass_action = function(url, selector, block_url, complete_cb, values_post_process_cb) {
//     var values = $(selector).getValues();
// 
// //     if(values_post_process_cb && $.isFunction(values_post_process_cb)){
//     if ($.isFunction(values_post_process_cb)) {
//         values = values_post_process_cb(values);
//     }
// 
//     if (values.length == 0) {
//         //creme.utils.showDialog(gettext("Nothing is selected."));
//         creme.dialogs.warning(gettext("Nothing is selected.")).open();
//         return;
//     }
// 
//     creme.blocks.confirmPOSTQuery(url, {blockReloadUrl: block_url}, {ids: values})
//                 .onDone(creme.emails._processDone)
//                 .start();
// /*
//     creme.utils.ajaxDelete(url,
//                            {ids: values},
//                            {
//                                 success: function(data, status, req) {
//                                     creme.utils.showDialog(gettext("Process done"));
//                                 },
//                                 complete: function(req, st) {
// //                                    if(block_url && typeof(block_url) != "undefined") {
//                                     if (block_url) {
//                                         creme.blocks.reload(block_url);
//                                     }
// 
//                                     if (st != 'error') {
// //                                        if (complete_cb && $.isFunction(complete_cb)) {
//                                         if ($.isFunction(complete_cb)) {
//                                            complete_cb();
//                                         }
// 
//                                    }
//                                    creme.utils.loading('loading', true);
//                                }
//                            });
// */
// };

// creme.emails.mass_relation = function(url, selector, block_url) {
//     var values = $(selector).getValues();
//     if (values.length == 0) {
//         creme.dialogs.warning(gettext("Please select at least one entity.")).open();
//         return false;
//     }
// 
//     url = creme.utils.appendInUrl(url, '?persist=ids&ids=' + values.join('ids='));
// 
//     creme.blocks.form(url, {blockReloadUrl: block_url}).open();
// };

// creme.emails.confirmResend = function(message, url, ids, block_url, complete_cb) {
creme.emails.confirmResend = function(message, ids, block_url) {
//     return creme.blocks.confirmAjaxQuery('/emails/mail/resend',
    return creme.blocks.confirmPOSTQuery('/emails/mail/resend',
                                         {blockReloadUrl: block_url,
                                          messageOnSuccess: gettext('Process done'),
                                          confirm: message
                                         },
                                         {ids: ids}
                                        )
//                        .onDone(creme.emails._processDone);
                       .start();
}

// creme.emails.resend = function(url, ids, block_url, complete_cb) {
creme.emails.resend = function(ids, block_url) {
//     return creme.blocks.ajaxQuery(url, {blockReloadUrl: block_url})
    return creme.blocks.ajaxPOSTQuery('/emails/mail/resend',
                                      {blockReloadUrl: block_url,
                                       messageOnSuccess: gettext('Process done')
                                      })
                       .data({ids: ids})
//                        .onDone(creme.emails._processDone)
                       .start();
/*
    creme.ajax.post({
            url: url,
            data: {'ids': ids},
            success: function(data, status, req) {
                    creme.utils.showDialog(gettext("Process done"));
            },
            complete: function(req, st) {
                if (st != 'error') {
//                     if (block_url && typeof(block_url) != "undefined") {
                    if (block_url) {
                        creme.blocks.reload(block_url);
                    }
//                     if (complete_cb && $.isFunction(complete_cb)) {
                    if ($.isFunction(complete_cb)) {
                        complete_cb();
                    }
                }
                creme.utils.loading('loading', true);
            }
        });
*/
}
