/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

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
 * Requires : jQuery, creme
 */

creme.persons = {};

//Copy only in the same order
creme.persons.copyTo = function (from_id, to_id) {
    var $from = $('#' + from_id);
    var $to = $('#' + to_id);
    if($from.size() > 0 && $to.size() > 0) {
        var $to_fill = $to.find('input, textarea, select');

        //TODO: use ':input' selector ??
        $from.find('input, textarea, select').each(function(ind) {
            $($to_fill[ind]).val($(this).val());
        });
    }
}

//TODO: rename postBecome
/*
creme.persons.post_become = function(atag, id_value) {
    $form = $('form', $(atag));
    $input = $('#id_become' , $form);
    $input.attr('value', id_value);

    $form.submit();
}
*/

creme.persons.become = function(url, organisations) {
    if (Object.isEmpty(organisations))
        return;

    if (organisations && organisations.length > 1) {
        creme.dialogs.choice(gettext('Select the concerned organisation.'), 
                             {choices: organisations, title: gettext('Organisation')})
                     .onOk(function(event, orga_id) {
                          creme.utils.ajaxQuery(url, {action:'post', reloadOnSuccess:true, warnOnFail:true}, {id: orga_id}).start();
                      })
                     .open();
    } else {
        creme.utils.ajaxQuery(url, {action:'post', reloadOnSuccess:true, warnOnFail:true}, {id: organisations[0].value}).start();
    }
}
