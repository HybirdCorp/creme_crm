/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2025  Hybird

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

creme.action = creme.action || {};

creme.action.ActionLink = creme.component.Component.sub({
    _init_: function(options) {
        this._options = $.extend({
            strict: false,
            debounce: 0
        }, options || {});

        this._running = false;
        this._events = new creme.component.EventHandler();
        this._registry = new creme.component.FactoryRegistry();
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
    },

    onComplete: function(listener, decorator) {
        this.on('action-link-done action-link-cancel action-link-fail', listener, decorator);
    },

    builders: function(builders) {
        if (builders instanceof creme.component.FactoryRegistry) {
            this._registry = builders;
        } else if (Object.isFunc(builders)) {
            this._registry = new creme.component.FactoryRegistry({
                fallback: builders
            });
        } else if (builders instanceof Object) {
            this._registry = new creme.component.FactoryRegistry({
                builders: builders
            });
        } else {
            throw Error('action builder "%s" is not valid'.format(builders));
        }

        return this;
    },

    trigger: function(event) {
        this._events.trigger(event, Array.from(arguments).slice(1), this);
        return this;
    },

    isRunning: function() {
        return this._running === true;
    },

    isBound: function() {
        return Object.isNone(this._button) === false;
    },

    isDisabled: function() {
        return this.isBound() && this._button.is('.is-disabled');
    },

    options: function() {
        return this._options;
    },

    _debounce: function(handler, delay) {
        if (delay > 0) {
            return _.debounce(handler, delay);
        } else {
            return handler;
        }
    },

    _optActionBuilder: function(button, actiontype) {
        return this._registry.get(actiontype, this.options().strict);
    },

    _optActionData: function(button) {
        var script = $('script[type$="/json"]', button);

        try {
            if (!Object.isEmpty(script)) {
                var data = _.readJSONScriptText(script.get(0));
                return Object.isEmpty(data) ? {} : JSON.parse(data);
            }
        } catch (e) {
            console.warn(e);
        }

        return {};
    },

    _optDebounceDelay: function(button) {
        var delay = parseInt(button.attr('data-debounce') || '');
        return isNaN(delay) ? this._options.debounce : delay;
    },

    bind: function(button) {
        if (this.isBound()) {
            throw Error('action link is already bound');
        }

        var url = button.attr('href') || button.attr('data-action-url');
        var actiontype = button.attr('data-action') || '';
        var isRunning = this.isRunning.bind(this);
        var isDisabled = this.isDisabled.bind(this);
        var trigger = this.trigger.bind(this);
        var setRunning = function(state) {
                             this._running = state;
                             button.toggleClass('is-loading', state);
                         }.bind(this);

        var debounceDelay = this._optDebounceDelay(button);
        var actiondata = this._optActionData(button);
        var builder = this._optActionBuilder(button, actiontype);
        var isvalid = Object.isFunc(builder);

        if (isvalid) {
            var actionHandler = this._debounce(function(e) {
                if (!isRunning()) {
                    var action = builder(url, actiondata.options, actiondata.data, e);

                    if (Object.isSubClassOf(action, creme.component.Action)) {
                        trigger('action-link-start', url, actiondata.options || {}, actiondata.data || {}, e);
                        setRunning(true);
                        action.one('done fail cancel', function() {
                                   setRunning(false);
                               })
                              .one({
                                  done: function() {
                                      trigger('action-link-done', Array.from(arguments).slice(1), this);
                                  },
                                  cancel: function() {
                                      trigger('action-link-cancel', Array.from(arguments).slice(1), this);
                                  },
                                  fail: function() {
                                      trigger('action-link-fail', Array.from(arguments).slice(1), this);
                                  }
                               })
                              .start();
                    } else {
                        console.warn('action link builder for "' + actiontype + '" have not returned an action instance : ', action);
                    }
                }
            }, debounceDelay);

            // the handler is deferred, not the event. This prevents default behaviour of links.
            this._onButtonClick = function(e) {
                e.preventDefault();
                e.stopPropagation();

                if (!isDisabled()) {
                    actionHandler(e);
                }
            };
        } else {
            button.addClass('is-disabled');
            console.warn('action link builder for "' + actiontype + '" does not exist.', button);

            this._onButtonClick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            };
        }

        button.on('click', this._onButtonClick);

        this._button = button;
        return this;
    },

    unbind: function() {
        if (this.isBound() === false) {
            throw Error('action link is not bound');
        }

        this._button.off('click', this._onButtonClick);
        this._button = undefined;
        this._onButtonClick = undefined;
    }
});

}(jQuery));
