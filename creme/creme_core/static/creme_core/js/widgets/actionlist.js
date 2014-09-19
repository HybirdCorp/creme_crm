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

creme.widget.ActionButton = creme.component.Action.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._delegate = delegate;
        this._button = button;

        this.onDone($.proxy(this._updateDelegate, this))
    },

    _updateDelegate: function(event, data)
    {
        var delegate = this._delegate;

        if (Object.isEmpty(delegate))
            return;

        var item = creme.utils.JSON.clean(data, null);

        if (item != null) {
            delegate.update(data);
        } else {
            delegate.reload();
        }
    },

    context: function(context) {
        return Object.property(this, '_context', context);
    },

    dependencies: function() {
        return [];
    }
});

creme.widget.ResetActionButton = creme.widget.ActionButton.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.widget.ActionButton, '_init_', delegate, button, options);
    },

    _run: function(options)
    {
        var options = creme.widget.parseopt(this.options().button, {value: ''});
        this._updateDelegate({value:options.value}, 'success');
    }
});

creme.widget.CreateActionButton = creme.widget.ActionButton.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.widget.ActionButton, '_init_', delegate, button, options);
    },

    _dialogOptions: function()
    {
        var options = creme.widget.parseopt(this._button, {popupResizable: true,
                                                           popupDraggable: true,
                                                           popupWidth: window.screen.width / 2,
                                                           popupHeight: 356,
                                                           url: '',
                                                           title: ''});

        options.url = new creme.utils.Template(options.url).render(this._context);
        return options;
    },

    _run: function(options)
    {
        var self = this;
        var action = new creme.dialog.FormDialogAction();

        action.onDone(function(event, data) {
                          self._updateDelegate(data);
                          self.done(data);
                      })
              .onCancel(function(event) {
                          self.cancel();
                      })
              .start(this._dialogOptions());
    }
});

creme.widget.ActionButtonList = creme.widget.declare('ui-creme-actionbuttonlist', {
    options: {
        debug: true
    },

    _create: function(element, options, cb, sync)
    {
        var self = this;
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._selector = creme.widget.create(self.selector(element), {disabled: !self._enabled});
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);
        this._context = {};

        if (!this._enabled) {
            element.attr('disabled', '');
            self.actions(element).attr('disabled', '');
        }

        self.actions(element).click(function() {
            self._handleAction(element, $(this));
            return false;
        });

        $(element).bind('action', function(e, name, listeners) {
            self.doAction(element, name, listeners);
        });

        creme.object.invoke(cb, element);
        element.addClass('widget-ready');
    },

    actions: function(element) {
        return $('> li > button.ui-creme-actionbutton', element);
    },

    action: function(element, name) {
        return $('> li > button.ui-creme-actionbutton[name="' + name + '"]', element);
    },

    doAction: function(element, name, listeners)
    {
        var button = this.action(element, name);

        if (button.length === 1) {
            this._handleAction(element, button, listeners);
        } else {
            this._selector.element.triggerHandler('action', [name, listeners]);
        }
    },

    selector: function(element) {
        return $('> li.delegate > .ui-creme-widget', element);
    },

    dependencies: function(element) {
        return creme.object.delegate(this._selector, 'dependencies') || [];
    },

    url: function(element, url)
    {
        if (url === undefined)
            return creme.object.delegate(this._selector, 'url');

        creme.object.delegate(this._selector, 'url', url);
        return this;
    },

    filter: function(element, filter)
    {
        if (filter === undefined)
            return creme.object.delegate(this._selector, 'filter');

        creme.object.delegate(this._selector, 'filter', filter);
        return this;
    },

    reload: function(element, data, cb, error_cb, sync)
    {
        creme.object.delegate(this._selector, 'reload', data, cb, error_cb, sync);
        this._context = $.extend({}, this._context || {}, data);
        return this;
    },

    val: function(element, value)
    {
        if (value === undefined)
            return creme.object.delegate(this._selector, 'val') || '';

        creme.object.delegate(this._selector, 'val', value);
        return this;
    },

    reset: function(element, value) {
        creme.object.delegate(this._selector, 'reset');
        return this;
    },

    cleanedval: function(element) {
        return creme.object.delegate(this._selector, 'cleanedval') || null;
    },

    update: function(element, data)
    {
        creme.object.delegate(this._selector, 'update');
        return this;
    },

    _handleAction: function(element, button, listeners)
    {
        var action = new creme.component.Action();
        var listeners = listeners || {};
        var actiontype = creme.widget.parseopt(button, {action:'popup'}).action;
        var builder = this['_action_' + actiontype];

        if (!this._enabled || !Object.isFunc(builder))
            return action.on(listeners).cancel();

        action = builder(this._selector, button);

        action.context(this._context)
              .onDone(function(event, data) {
                   element.triggerHandler('actionSuccess', [data]);
               })
              .onCancel(function(event) {
                   element.triggerHandler('actionCanceled');
               })
              .on(listeners)
              .start();

        return action;
    },

    _action_reset: function(selector, button) {
        return new creme.widget.ResetActionButton(selector, button);
    },

    _action_popup: function(selector, button) {
        return new creme.widget.CreateActionButton(selector, button);
    }
});
