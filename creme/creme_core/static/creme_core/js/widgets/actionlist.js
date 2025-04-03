/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

creme.widget.SelectorAction = creme.component.Action.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.component.Action, '_init_', this._run, options);
        this._delegate = delegate;
        this._button = button;

        this.onDone(this._updateDelegate.bind(this));
    },

    _updateDelegate: function(event, data) {
        var delegate = this._delegate;

        if (Object.isEmpty(delegate)) {
            return;
        }

        data = _.isString(data) ? _.cleanJSON(data) || null : data;

        if (data !== null) {
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

creme.widget.ResetSelectorAction = creme.widget.SelectorAction.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.widget.SelectorAction, '_init_', delegate, button, options);
    },

    _run: function(options) {
        var buttonOptions = creme.widget.parseopt(this._button, {value: ''});
        this.done({value: buttonOptions.value}, 'success');
    }
});

creme.widget.CreateSelectorAction = creme.widget.SelectorAction.sub({
    _init_: function(delegate, button, options) {
        this._super_(creme.widget.SelectorAction, '_init_', delegate, button, options);
    },

    _dialogOptions: function() {
        var options = creme.widget.parseopt(this._button, {
            popupResizable: true,
            popupDraggable: true,
            popupWidth: window.screen.width / 2,
            popupHeight: 356,
            popupUrl: '',
            popupTitle: ''
        });

        var delegate = this._delegate;
        var context = Object.isFunc(delegate.context) ? {_delegate_: delegate.context()} : {};
        context = $.extend(context, this._context);

        options.url = new creme.utils.Template(options.popupUrl).render(context);
        options.title = new creme.utils.Template(options.popupTitle).render(context);
        return options;
    },

    updateButtonState: function() {
        var dialogOptions = this._dialogOptions();
        var label = dialogOptions.title || gettext('Add');

        this._button.toggleProp('disabled', Object.isEmpty(dialogOptions.url))
                    .find('span').text(label);
    },

    _run: function(options) {
        var self = this;
        var dialogOptions = this._dialogOptions();

        if (Object.isEmpty(dialogOptions.url)) {
            self.cancel();
            return;
        }

        var action = new creme.dialog.FormDialogAction();

        action.onDone(function(event, data) {
                   self.done(data.data());
               })
              .on('cancel fail', function(event) {
                   self.cancel();
               })
              .start(dialogOptions);
    }
});

creme.widget.SelectorActionBuilderRegistry = creme.action.DefaultActionBuilderRegistry.sub({
    _init_: function(selector) {
        this._selector = selector;
        this._super_(creme.action.DefaultActionBuilderRegistry, '_init_');
    },

    _build_popup: function(url, options, data) {
        return new creme.widget.CreateSelectorAction(this._selector, options.button).context(data || {});
    },

    _build_reset: function(url, options, data) {
        return new creme.widget.ResetSelectorAction(this._selector, options.button).context(data || {});
    }
});


creme.widget.ActionButtonList = creme.widget.declare('ui-creme-actionbuttonlist', {
    options: {
        backend: undefined,
        debug: true
    },

    _create: function(element, options, cb, sync) {
        var self = this;
        this._enabled = creme.object.isFalse(options.disabled) && element.is(':not([disabled])');
        this._selector = creme.widget.create(self.selector(element), {disabled: !self._enabled, backend: options.backend});
        this._dependencies = Array.isArray(options.dependencies) ? options.dependencies : (options.dependencies ? options.dependencies.split(' ') : []);
        this._context = {};
        this._actionBuilders = new creme.widget.SelectorActionBuilderRegistry(this._selector);

        if (!this._enabled) {
            element.attr('disabled', '');
            self.actionButtons(element).attr('disabled', '');
        }

        self.actionButtons(element).on('click', function(e) {
            e.preventDefault();
            self._onButtonActionClick(element, $(this));
        });

        $(element).on('action', function(e, name, listeners) {
            self.doAction(element, name, listeners);
        });

        creme.object.invoke(cb, element);
        element.addClass('widget-ready');
    },

    actionButtons: function(element) {
        return $('> li > button.ui-creme-actionbutton', element);
    },

    actionButton: function(element, name) {
        return $('> li > button.ui-creme-actionbutton[name="' + name + '"]', element);
    },

    doAction: function(element, name, listeners) {
        listeners = listeners || {};
        var button = this.actionButton(element, name);

        if (button.length === 1) {
            this._doAction(element, button, listeners);
        } else {
            this._selector.element.triggerHandler('action', [name, listeners]);
        }
    },

    isDisabled: function(element) {
        return !this._enabled;
    },

    selector: function(element) {
        return $('> li.delegate > .ui-creme-widget', element);
    },

    dependencies: function(element) {
        return creme.object.delegate(this._selector, 'dependencies') || [];
    },

    url: function(element, url) {
        if (url === undefined) {
            return creme.object.delegate(this._selector, 'url');
        }

        creme.object.delegate(this._selector, 'url', url);
        return this;
    },

    filter: function(element, filter) {
        if (filter === undefined) {
            return creme.object.delegate(this._selector, 'filter');
        }

        creme.object.delegate(this._selector, 'filter', filter);
        return this;
    },

    reload: function(element, data, cb, error_cb, sync) {
        creme.object.delegate(this._selector, 'reload', data, cb, error_cb, sync);
        this._context = $.extend({}, this._context || {}, data);
        this._updateActionButtons(element);
        return this;
    },

    val: function(element, value) {
        if (value === undefined) {
            return creme.object.delegate(this._selector, 'val') || '';
        }

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

    update: function(element, data) {
        creme.object.delegate(this._selector, 'update');
        return this;
    },

    _updateActionButtons: function(element) {
        var self = this;

        this.actionButtons(element).each(function() {
            var action = self._buildAction(element, $(this));

            if (Object.isFunc(action.updateButtonState)) {
                action.updateButtonState();
            }
        });
    },

    _buildAction: function(element, button) {
        // TODO : rename "popup" to "create"
        var actiontype = creme.widget.parseopt(button, {action: 'popup'}).action;
        var builder = this._actionBuilders.get(actiontype);

        if (Object.isFunc(builder)) {
            return builder('', {button: button}, this._context);
        } else {
            return new creme.component.Action(function() {
                this.cancel();
            });
        }
    },

    _doAction: function(element, button, listeners) {
        listeners = listeners || {};

        var action = this._buildAction(element, button);

        action.onDone(function(event, data) {
                   element.trigger('actionListSuccess', data);
               })
              .on('cancel fail', function(event) {
                   element.trigger('actionListCanceled', Array.from(arguments).slice(1));
               })
              .one(listeners)
              .start();

        return action;
    },

    _onButtonActionClick: function(element, button) {
        if (this.isDisabled() || button.is('[disabled]')) {
            return;
        }

        this._doAction(element, button);
    }
});

}(jQuery));
