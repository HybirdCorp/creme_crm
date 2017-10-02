/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2015-2017  Hybird

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
            strict: false
        }, options || {});

        this._running = false;
        this._events = new creme.component.EventHandler();
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
        return Object.property(this, '_builders', builders);
    },

    trigger: function(event) {
        this._events.trigger(event, Array.copy(arguments).slice(1), this);
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

    _getActionBuilder: function(button, actiontype) {
        try {
            var builders = this.builders() || {};
            return Object.isFunc(builders) ? builders(actiontype) : builders['_action_' + actiontype].bind(builders);
        } catch (e) {
            console.warn(e);
        }
    },

    _getActionData: function(data) {
        try {
            return Object.isEmpty(data) ? {} : JSON.parse(data);
        } catch (e) {
            console.warn(e);
            return {};
        }
    },

    bind: function(button) {
        if (this.isBound()) {
            throw Error('action link is already bound');
        }

        var url = button.attr('href') || button.attr('data-action-url');
        var enabled = button.is(':not(.is-disabled)');
        var actiontype = (button.attr('data-action') || '').replace(/\-/g, '_').toLowerCase();
        var isRunning = this.isRunning.bind(this);
        var trigger = this.trigger.bind(this);
        var setRunning = function(state) {
                             this._running = state;
                             button.toggleClass('is-loading', state);
                         }.bind(this);

        var actiondata = this._getActionData($('script:first', button).text());
        var builder = this._getActionBuilder(button, actiontype);
        var isvalid = Object.isFunc(builder);

        // TODO : see for a more straight forward method for handling of missing actions in both strict/not strict modes.
        if (!isvalid) {
            if (this._options.strict) {
                throw Error('no such action "' + actiontype + '"');
            } else {
                console.warn(button, 'no such action "' + actiontype + '" with', actiondata);
            }
        }

        if (isvalid && enabled) {
            var handler = function(e) {
                e.preventDefault();
                e.stopPropagation();

                if (!isRunning()) {
                    var action = builder(url, actiondata.options, actiondata.data, e);

                    if (Object.isNone(action) === false) {
                        trigger('action-link-start', url, actiondata.options || {}, actiondata.data || {});
                        setRunning(true);
                        action.onComplete(function() {
                                   setRunning(false);
                               })
                              .on({
                                  error: function(e, key, data, listener) {
                                      trigger('action-link-error', Array.copy(arguments).slice(1), this);
                                  },
                                  done: function() {
                                      trigger('action-link-done', Array.copy(arguments).slice(1), this);
                                  },
                                  cancel: function() {
                                      trigger('action-link-cancel', Array.copy(arguments).slice(1), this);
                                  },
                                  fail: function() {
                                      trigger('action-link-fail', Array.copy(arguments).slice(1), this);
                                  }
                               })
                              .start();
                    }
                }
            };

            button.click(handler);
        } else {
            button.addClass('is-disabled');
            button.click(function(e) {
                e.preventDefault();
                trigger('action-link-start');
                setRunning(false);
                trigger('action-link-cancel', []);
                return false;
            });
        }

        this._button = button;
        return this;
    }
});

}(jQuery));
