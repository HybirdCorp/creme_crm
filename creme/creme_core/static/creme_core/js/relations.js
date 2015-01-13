/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2015  Hybird

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
 * Requires : creme, jQuery
 */

creme.relations = creme.relations || {};

creme.relations.addRelationTo = function(subject, predicate, ctype, options, data) {
    var options = options || {};
    var query = new creme.ajax.Backend().query().url('/creme_core/relation/add_from_predicate/save');

    if (options.blockReloadUrl) {
        query.onDone(function(event, data) {creme.blocks.reload(options.blockReloadUrl);});
    } else {
        query.onDone(function(event, data) {creme.utils.reload(window);});
    }

    var url = '/creme_core/relation/objects2link/rtype/%s/entity/%s/%s%s'.format(predicate, subject, ctype,
                                                                                 options.multiple ? '' : '/simple');

    var action = creme.lv_widget.listViewAction(url, options, data);
    action.onDone(function(event, data) {
        query.post({
                  entities: data,
                  subject_id: subject,
                  predicate_id: predicate
              });
    });

    return action.start();
}
