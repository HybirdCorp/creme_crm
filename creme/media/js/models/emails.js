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

creme.emails.mass_action = function(url, selector, block_url)
{
    var values = $(selector).getValues();

    creme.utils.ajaxDelete(url,
                           {'ids': values},
                           {
                               success : function(data, status, req){
                                    creme.utils.showDialog("Opération effectuée");
                                },
                               complete:function(req, st){if(st!='error'){creme.utils.loadBlock(block_url);}
                                   creme.utils.loading('loading', true);}
                           });
    
};



creme.emails.mass_relation = function(url, selector, block_url)
{
    var values = $(selector).getValues();
    if(values.length == 0)
    {
        creme.utils.showDialog(i18n.get_current_language()['SELECT_AT_LEAST_ONE_ENTITY']);
        return false;
    }

    url += values.join(',')+',';

    creme.utils.innerPopupNReload(url, block_url);
};