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
 * Requires : creme, jQuery, creme.bricks
 */

(function($) {
"use strict";

creme.crudity = {};

var waitingSyncActions = {
    'crudity-validate': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
    },

    'crudity-validate-row': function(url, options, data, e) {
        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: [data.id]}, e);
    },

    'crudity-delete': function(url, options, data, e) {
        var values = this._selectedRowValues().filter(Object.isNotEmpty);

        if (values.length === 0) {
            return this._warningAction(gettext('Nothing is selected.'));
        }

        return this._build_update(url, {messageOnSuccess: gettext('Process done')}, {ids: values}, e);
    }
};

$(document).on('brick-setup-actions', '.brick.crudity-actions-brick', function(e, brick, actions) {
    actions.registerAll(waitingSyncActions);
});

creme.crudity.RefreshSyncStatusAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _reloadCrudityDeps: function(backends) {
        var self = this;
        var dependencies = new creme.bricks.Dependencies([]);

        $('.brick').each(function() {
            var brick = $(this);

            if (backends.indexOf(brick.attr('data-crudity-backend')) !== -1) {
                dependencies.add(brick.creme().widget().brick().dependencies());
            }
        });

        var reload = new creme.bricks.BricksReloader()
                                     .dependencies(dependencies)
                                     .action();

        reload.on({
            fail: function(event, error) { self.fail(error); },
            'done cancel': function() { self.done(backends); }
        });

        return reload.start();
    },

    _run: function(options) {
        options = $.extend({}, this.options(), options || {});

        var self = this;
        var query = creme.ajax.query(options.url || '', {
            action: 'post'
        });

        query.onFail(function(event, error) {
                  if (options.warnOnFail) {
                      creme.dialogs.warning(error)
                                   .onClose(function() { self.fail(error); })
                                   .open();
                  } else {
                      self.fail(error);
                  }
              })
             .onDone(function(event, data) {
                  data = _.cleanJSON(data) || [];

                  if (Array.isArray(data) && !Object.isEmpty(data)) {
                      return self._reloadCrudityDeps(data);
                  } else {
                      self.done(data);
                  }
              })
             .start();
    }
});

var CrudityActionBuilderRegistry = creme.component.FactoryRegistry.sub({
    _build_crudity_hatbar_refresh: function(url, options, data, e) {
        return new creme.crudity.RefreshSyncStatusAction({
            url: url,
            warnOnFail: true
        });
    }
});


creme.crudity.CrudityHatController = creme.component.Component.sub({
    _init_: function() {
        this._builders = new CrudityActionBuilderRegistry();
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('CrudityHatController is already bound');
        }

        this._element = element;
        var builders = this._builders;

        element.find('a[data-action]').each(function() {
            new creme.action.ActionLink().builders(builders).bind($(this));
        });

        return this;
    },

    refresh: function(delay) {
        if (this.isBound() === false) {
            return this;
        }

        var self = this;

        if (this._timeout) {
            clearTimeout(this._timeout);
        }

        this._timeout = setTimeout(function() {
            self._timeout = undefined;
            self._element.find('a[data-action="crudity-hatbar-refresh"]').trigger('click');
        }, delay || 0);

        return this;
    }
});

}(jQuery));
