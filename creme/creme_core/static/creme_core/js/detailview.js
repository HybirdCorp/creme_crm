/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2017-2025  Hybird

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

/* NB: these actions are only available in detail-view for non-CremeEntity models
   ( "creme_core/generics/view_entity.html" uses a Brick with the buttons, so brick-actions are used instead).
   TODO: should we used a Brick in all cases (to get a powerful reloading system -- and remove the code below) ?
         The hat bar should be a true Brick too?
 */
    var menuBarActions = {
        'creme_core-hatmenubar-view': function(url, options, data) {
            options = $.extend(creme.bricks.defaultDialogOptions(url, data.title), options || {});
            return new creme.bricks.DialogAction(options);
        },

        'creme_core-hatmenubar-form': function(url, options, data) {
            options = $.extend(creme.bricks.defaultDialogOptions(url, data.title), options || {});
            return new creme.bricks.FormDialogAction(options);
        },

        'creme_core-hatmenubar-update': function(url, options, data) {
            return this._postQueryAction(url, options, data);
        },

        'creme_core-hatmenubar-update-redirect': function(url, options, data) {
            return this._postQueryAction(url, options).onDone(function() {
                creme.utils.goTo(data.redirect);
            });
        }
    };

    creme.views.HatMenuBar = creme.widget.declare('ui-creme-hatmenubar', {
        _create: function(element, options, cb, sync, args) {
            var builder = this._builder = new creme.action.DefaultActionBuilderRegistry();
            var buttons = $('[data-action]', element);

            builder.registerAll(menuBarActions);

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
}(jQuery));
