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

(function($) {
"use strict";

creme.relations = creme.relations || {};

creme.relations.AddRelationToAction = creme.component.Action.sub({
    _init_: function(options) {
        options = options || {};

        if (Object.isEmpty(options.addto_url)) {
            options.addto_url = $('body').attr('data-save-relations-url');
        }

        if (Object.isEmpty(options.selector_url)) {
            options.selector_url = $('body').attr('data-select-relations-objects-url');
        }

        this._super_(creme.component.Action, '_init_', this._addRelationTo, options);
    },

    _updateQuery: function(selection, options) {
        var self = this;
        var query = creme.ajax.query(options.addto_url || '');

        if (options.reloadOnSuccess) {
            query.onDone(function() {
                creme.utils.reload();
                self.done();
            }).onCancel(function() {
                self.cancel();
            }).onFail(function(e, data) {
                self.fail(data);
            });
        } else {
            var deps = new creme.bricks.BricksReloader().dependencies([
                                                            'creme_core.relation',
                                                            'creme_core.relation.' + options.rtype_id
                                                         ])
                                                        .action();

            deps.after(query).on('cancel done', function() {
                self.done();
            }).onFail(function() {
                self.fail();
            });
        }

        return query;
    },

    _addRelationTo: function(options) {
        options = $.extend(this.options(), options || {});

        var self = this;
        var selectorUrl = options.selector_url || '';
        var selectorOptions = {
            multiple: options.multiple || false
        };
        var selectorData = {
            subject_id:    options.subject_id,
            rtype_id:      options.rtype_id,
            objects_ct_id: options.ctype_id
        };

        var selector = creme.lv_widget.listViewAction(selectorUrl, selectorOptions, selectorData);
        selector.onDone(function(event, data) {
                     self._updateQuery(data, options).post({
                         entities: data,
                         subject_id: options.subject_id,
                         predicate_id: options.rtype_id
                     });
                 })
                .on({
                    fail: function() {
                        self.fail();
                    },
                    cancel: function() {
                        self.cancel();
                    }
                 })
                .start();
    }
});

creme.relations.addRelationTo = function(subject_id, rtype_id, ctype_id, options) {
    console.warn('creme.relations.addRelationTo is deprecated. Use AddRelationToAction or <a data-action="add-relationships" ...> in bricks');
    return creme.relations.AddRelationToAction($.extend({
        subject_id: subject_id,
        rtype_id: rtype_id,
        ctype_id: ctype_id
    }, options || {})).start();
};

}(jQuery));
