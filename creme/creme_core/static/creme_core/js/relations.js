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
 * Requires : creme.ajax, creme.lv_widget, creme.bricks, jQuery
 */

(function($) {"use strict";

creme.relations = creme.relations || {};

creme.relations.addRelationTo = function(subject_id, rtype_id, ctype_id, options, data) {
    var $body = $('body');
    var save_url = $body.attr('data-save-relations-url');
    var selection_url = $body.attr('data-select-relations-objects-url');
    var query = new creme.ajax.Backend().query().url(save_url);
    var options = options || {};
    var reload_on_success = options.reloadOnSuccess;

    if (reload_on_success === 'window') {
        query.onDone(function(event, data) {creme.utils.reload(window);});
    } else if (reload_on_success !== false) {
        query.onDone(function() {new creme.bricks.BricksReloader().dependencies(['creme_core.relation', 'creme_core.relation.' + rtype_id]).action().start();});
    }

    var get_data = $.extend({
        subject_id:    subject_id,
        rtype_id:      rtype_id,
        objects_ct_id: ctype_id,
        selection:     options.multiple ? 'multiple' : 'single'
    }, data || {});

    var action = creme.lv_widget.listViewAction(selection_url, {multiple: options.multiple ? true : false}, get_data);
    action.onDone(function(event, data) {
        query.post({
                  entities: data,
                  subject_id: subject_id,
                  predicate_id: rtype_id
              });
    });

    return action.start();
};

}(jQuery));
