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
 * Requires : jQuery
 *            creme
 *            
 */

creme.menu = {};

creme.menu.actions = {};

creme.menu.actions.flatMenu = function(trigger_selector, content_selector){
    $(trigger_selector).menu({
            content: $(content_selector).html(),
            showSpeed: 400
    });
    
    $('[role=menuitem]','[aria-labelledby="'+trigger_selector.replace('#','')+'"]')
    .live('menu-item-selected', function(e, menu){
        e.stopImmediatePropagation();

        var $a = $('a:first',this);

        if($a.hasClass('confirm_delete'))
        {
            creme.utils.confirmDelete2($a.attr('href'));
        }
        else
        {
            creme.utils.go_to($a.attr('href'));
        }
    });
};