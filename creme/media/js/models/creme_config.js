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

// Remove this when the block system is used. (15 may 2010 -> only old mail signature still uses this js)

var config = {};
config.setOrder = function(value) {
    var order = document.getElementById('order');
    if(order)
        order.value = value;
    else if(window.console)
        window.console.error('Mettez 2 input dans le form avec comme name & id order et way');

    var way = document.getElementById('way');
    if(way)
    {
        if(way.value == "")
            way.value = "-";
        else
            way.value = "";
    }
    else if(window.console)
        window.console.error('Mettez 2 input dans le form avec comme name & id order et way');
}

config.handleSort = function(sort_order, form_name)
{
    config.setOrder(sort_order);
    document.forms[form_name].submit();
}