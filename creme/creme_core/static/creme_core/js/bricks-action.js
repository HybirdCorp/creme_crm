/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2018  Hybird

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

(function($) {
"use strict";

creme.bricks = creme.bricks || {};

creme.bricks.DialogAction = creme.dialog.DialogAction.sub({
    _init_: function(options, listeners) {
        this._super_(creme.dialog.DialogAction, '_init_', options, listeners);
    },

    _buildPopup: function(options) {
        var popup = this._super_(creme.dialog.DialogAction, '_buildPopup', options);

        return popup.on('frame-activated', function() {
            creme.bricks.dialogActionButtons(this);
            creme.bricks.dialogCenterPosition(this);
        });
    }
});

creme.bricks.FormDialogAction = creme.dialog.FormDialogAction.sub({
    _init_: function(options, listeners) {
        this._super_(creme.dialog.FormDialogAction, '_init_', options, listeners);
    },

    _buildPopup: function(options) {
        var popup = this._super_(creme.dialog.FormDialogAction, '_buildPopup', options);

        return popup.on('frame-update', function() {
            creme.bricks.dialogCenterPosition(this);
        });
    }
});

creme.bricks.BrickActionLink = creme.action.ActionLink.sub({
    _init_: function(brick, options) {
        this._super_(creme.action.ActionLink, '_init_', options);
        this._brick = brick;
        this.builders(this._brickActionBuilder.bind(this));
    },

    _brickActionBuilder: function(actiontype) {
        var brick = this._brick;
        var builder = brick._getActionBuilder(actiontype);

        if (Object.isFunc(builder)) {
            return function(url, options, data, e) {
                if (!brick.isLoading()) {
                    brick.closeMenu();
                    return builder(url, options || {}, data || {}, e);
                }
            };
        }
    }
});

creme.bricks.BrickActionBuilders = creme.action.ActionBuilderRegistry.sub({
    _init_: function(brick) {
        this._brick = brick;
        this._super_(creme.action.ActionBuilderRegistry, '_init_');
    },

    _toggleStateAction: function(key, event, active_label, inactive_label) {
        var toggle = this._brick.toggleState.bind(this._brick, key);

        return new creme.component.Action(function() {
            var state = toggle().state()[key];

            if (!Object.isNone(event)) {
                var link = $(event.target).parents('[data-action]:first');
                link.find('.brick-action-title').text(state ? inactive_label : active_label);
            }

            this.done();
        });
    },

    _warningAction: function(message) {
        return new creme.component.Action(function() {
            var self = this;
            creme.dialogs.warning(message)
                         .onClose(function() {
                             self.fail();
                          })
                         .open();
        });
    },

    _updateAction: function(url, options, data) {
        options = $.extend({action: 'post'}, options || {});

        if (options.confirm) {
            return creme.utils.confirmAjaxQuery(url, options, data);
        } else {
            return creme.utils.ajaxQuery(url, options, data);
        }
    },

    _selectedRowValues: function(getter) {
        var selected = this._brick.table().selections().selected();
        getter = getter || function(item) {
            return item.ui.find('input').val();
        };

        return selected.map(getter);
    },

    _refreshBrick: function() {
        return this._brick.refresh();
    },

    _build_view: function(url, options, data) {
        options = $.extend(this._brick._defaultDialogOptions(url, data.title), options || {});

        return new creme.bricks.DialogAction(options);
    },

    _build_redirect: function(url, options, data) {
        var context = $.extend({}, data || {}, {
            location: window.location.href.replace(/.*?:\/\/[^\/]*/g, '') // remove 'http://host.com'
        });

        return new creme.component.Action(function() {
            creme.utils.goTo(creme.utils.templatize(url, context).render());
            this.done();
        });
    },

    _build_collapse: function(url, options, data, event) {
        return this._toggleStateAction('collapsed', event, data.inlabel, data.outlabel);
    },

    _build_reduce_content: function(url, options, data, event) {
        return this._toggleStateAction('reduced', event, data.inlabel, data.outlabel);
    },

    _build_form: function(url, options, data) {
        options = $.extend(this._brick._defaultDialogOptions(url), options || {});
        return new creme.bricks.FormDialogAction(options);
    },

    _build_form_refresh: function(url, options, data) {
        return this._build_form(url, options, data).onDone(this._refreshBrick.bind(this));
    },

    _build_add: function(url, options, data) {
        return this._build_form_refresh(url, options, data);
    },

    _build_edit: function(url, options, data) {
        return this._build_form_refresh(url, options, data);
    },

    _build_link: function(url, options, data) {
        return this._build_form_refresh(url, options, data);
    },

    _build_delete: function(url, options, data) {
        options = $.extend({}, options || {}, {confirm: true});
        return this._updateAction(url, options, data).onDone(this._refreshBrick.bind(this));
    },

    _build_update: function(url, options, data) {
        return this._updateAction(url, options, data).onDone(this._refreshBrick.bind(this));
    },

    _build_update_redirect: function(url, options, data) {
        return this._updateAction(url, options, data).onDone(function(event, data, xhr) {
            creme.utils.goTo(data);
        });
    },

    _build_add_relationships: function(url, options, data) {
        // NOTE: the options parameter here is never used/filled at the moment, options are actually passed as __name=value
        //       and available in the data parameter. The only other option in creme.relations.addRelationTo being __mutiple.
        var action = new creme.relations.AddRelationToAction({
            subject_id: data.subject_id,
            rtype_id: data.rtype_id,
            ctype_id: data.ctype_id,
            addto_url: url,
            selector_url: data.selector_url,
            multiple: data.multiple,
            reloadOnSuccess: data.reloadOnSuccess
        });

        return action;
    }
});

}(jQuery));
