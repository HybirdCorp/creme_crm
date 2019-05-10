/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017-2019  Hybird

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
 * Requires : jQuery lib, creme.utils, creme.lv_widget.
 */

(function($) {
    "use strict";

    var detailViewActions = {
        'creme_core-detailview-merge': function(url, options, data) {
            var action = new creme.lv_widget.ListViewDialogAction({
                url: data.selection_url,
                selectionMode: 'single',
                data: {
                    id1: data.id
                }
            });

            action.onDone(function(event, selections) {
                creme.utils.goTo(url, {id1: data.id, id2: selections[0]});
            });

            return action;
        },

        'creme_core-detailview-clone': function(url, options, data) {
            return this._build_update_redirect(url, options, data);
        },

        'creme_core-detailview-delete': function(url, options, data) {
            return this._build_update_redirect(url, options, data);
        },

        'creme_core-detailview-restore': function(url, options, data) {
            return this._build_update_redirect(url, options, data);
        }
    };

    $(document).on('brick-setup-actions', '.brick.brick-hat', function(e, brick, actions) {
        actions.registerAll(detailViewActions);
    });

    creme.views = creme.views || {};

    // TODO : temporary widget. We should use a brick instead.
    creme.views.HatMenuBar = creme.widget.declare('ui-creme-hatmenubar', {
        _create: function(element, options, cb, sync, args) {
            var builder = this._builder = new creme.action.DefaultActionBuilderRegistry();
            var buttons = $('.menu_button[data-action]', element);

            $(element).trigger('hatmenubar-setup-actions', [builder]);

            this._actionlinks = buttons.map(function() {
                return new creme.action.ActionLink().builders(builder).bind($(this));
            }).get();

            element.addClass('widget-ready');
            creme.object.invoke(cb, element);
        },

        _destroy: function(element) {
            this._actionlinks.forEach(function(link) {
                link.unbind();
            });
        }
    });

    var menuBarActions = {
        'creme_core-hatmenubar-addrelationships': function(url, options, data) {
            var action = new creme.relations.AddRelationToAction({
                subject_id: data.subject_id,
                rtype_id: data.rtype_id,
                ctype_id: data.ctype_id,
                addto_url: url,
                selector_url: data.selector_url,
                multiple: true,
                reloadOnSuccess: true
            });

            return action;
        }
    };

    $(document).on('hatmenubar-setup-actions', '.ui-creme-hatmenubar', function(e, actions) {
        actions.registerAll(menuBarActions);
    });

}(jQuery));
