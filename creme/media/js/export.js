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
 * Requires : jQuery lib, creme declaration
 */

creme._export = {};

creme._export.select_one = function(evt, a)
{
    evt.preventDefault();
    var current_href = $(a).attr('href');

    var me = this;

    this.okDialogHandler = function(ui){
        current_href = current_href.replace('%s', $(ui).find('select').val());
        $(ui).dialog("destroy");
        $(ui).remove();
        window.location.href=current_href;
    }

    var $select = $('<select></select>');
    //Make dynamics values
    $select.append($('<option></option>').val("odt").text("Document open-office (ODT)"));
//    $select.append($('<option></option>').val("pdf").text("Fichier Pdf (PDF)"));

    creme.utils.showDialog($select, {title: '', modal: true, buttons: {"Ok": function(){me.okDialogHandler($(this))}}});

}
