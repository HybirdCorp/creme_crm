/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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

creme.emails.mass_action = function(url, selector, block_url, complete_cb) {
    var values = $(selector).getValues();

    creme.utils.ajaxDelete(url,
                           {'ids': values},
                           {
                               success : function(data, status, req){
                                    creme.utils.showDialog(gettext("Process done"));
                                },
                               complete:function(req, st){
                                   if(st!='error') {
                                       if(block_url && typeof(block_url) != "undefined") {
                                            creme.utils.loadBlock(block_url);
                                       }
                                       if(complete_cb && $.isFunction(complete_cb)) {
                                           complete_cb();
                                       }

                                   }
                                   creme.utils.loading('loading', true);
                               }
                           });
};

creme.emails.mass_relation = function(url, selector, block_url) {
    var values = $(selector).getValues();
    if(values.length == 0) {
        creme.utils.showDialog(gettext("Please select at least one entity."));
        return false;
    }

    url += values.join(',') + ',';

    creme.utils.innerPopupNReload(url, block_url);
};

creme.reload_synchronisation = function($target, target_url) {
    creme.ajax.get({
        url : target_url,
        success : function(data){
            $target.empty().html(data);
        }
    });
};

creme.emails.resend = function(url, ids, block_url, complete_cb) {
    creme.ajax.post({
            'url': url,
            'data': {'ids': ids},
            success : function(data, status, req) {
                    creme.utils.showDialog(gettext("Process done"));
                },
            complete: function(req, st) {
                if(st!='error') {
                    if(block_url && typeof(block_url) != "undefined") {
                        creme.utils.loadBlock(block_url);
                    }
                    if(complete_cb && $.isFunction(complete_cb)) {
                        complete_cb();
                    }
                }
                creme.utils.loading('loading', true);
            }
        });
}