 /*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2025 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

var _ActionStatus = {
    DONE: 'done',
    RUNNING: 'run',
    FAIL: 'fail',
    CANCEL: 'cancel'
};

creme.component.ActionStatus = $.extend({}, _ActionStatus);

// TODO: 'creme.component' =>  'creme.action' (already defined in action-link.js)
creme.component.Action = creme.component.Component.sub({
    _init_: function(action, options) {
        this._events = new creme.component.EventHandler();
        this._options = options || {};
        this._status = _ActionStatus.DONE;
        this._action = Object.isFunc(action) ? action : this.done;
    },

    start: function() {
        if (this.isRunning() === true) {
            return this;
        }

        try {
            this._events.trigger('start', Array.from(arguments), this);
            this._status = _ActionStatus.RUNNING;
            this._action.apply(this, Array.from(arguments));
        } catch (e) {
            console.error(e);
            this.fail(e);
        }

        return this;
    },

    done: function() {
        if (this.isRunning() === false) {
            return this;
        }

        this._status = _ActionStatus.DONE;
        this._events.trigger('done', Array.from(arguments), this);
        return this;
    },

    fail: function() {
        if (this.isRunning() === false) {
            return this;
        }

        this._status = _ActionStatus.FAIL;
        this._events.trigger('fail', Array.from(arguments), this);
        return this;
    },

    cancel: function() {
        if (this.isRunning() === false) {
            return this;
        }

        this._status = _ActionStatus.CANCEL;
        this._events.trigger('cancel', Array.from(arguments), this);
        return this;
    },

    trigger: function(event) {
        this._events.trigger(event, Array.from(arguments).slice(1), this);
        return this;
    },

    action: function(data) {
        var self = this;
        var action = (data === undefined || Object.isFunc(data)) ? data : function() { self.done(data); };
        return Object.property(this, '_action', action);
    },

    one: function(key, listener, decorator) {
        this._events.one(key, listener, decorator);
        return this;
    },

    on: function(key, listener, decorator) {
        return this.bind(key, listener, decorator);
    },

    off: function(key, listener) {
        return this.unbind(key, listener);
    },

    bind: function(key, listener, decorator) {
        this._events.bind(key, listener, decorator);
        return this;
    },

    unbind: function(key, listener) {
        this._events.unbind(key, listener);
        return this;
    },

    onStart: function(start) {
        return this.bind('start', start);
    },

    onComplete: function(complete) {
        return this.bind('done fail cancel', complete);
    },

    onDone: function(success) {
        return this.bind('done', success);
    },

    onCancel: function(canceled) {
        return this.bind('cancel', canceled);
    },

    onFail: function(error) {
        return this.bind('fail', error);
    },

    isRunning: function() {
        return this._status === _ActionStatus.RUNNING;
    },

    isStatusDone: function() {
        return this._status === _ActionStatus.DONE;
    },

    isStatusFail: function() {
        return this._status === _ActionStatus.FAIL;
    },

    isStatusCancel: function() {
        return this._status === _ActionStatus.CANCEL;
    },

    status: function() {
        return this._status;
    },

    options: function(options) {
        return Object.property(this, '_options', options);
    },

    listen: function(source, options) {
        return this.after(source, options);
    },

    stack: function() {
        var stack = [];
        var source = this._source;

        while (Object.isNone(source) === false) {
            stack.push(source);
            source = source._source;
        }

        return stack;
    },

    after: function(source, options) {
        options = $.extend({
            passArgs: false
        }, options || {});

        if (Object.isSubClassOf(source, creme.component.Action) === false) {
            throw new Error('This is not an action instance', source);
        }

        if (Object.isNone(this._source) === false) {
            throw new Error('Action is already after', this._source);
        }

        this._source = source;

        var self = this;

        source.onDone(function() {
            self.start.apply(self, options.passArgs ? Array.from(arguments).slice(1) : []);
        });

        source.onFail(function(event) {
            self._status = _ActionStatus.FAIL;
            self._events.trigger('fail', Array.from(arguments).slice(1), self);
        });

        source.onCancel(function(event) {
            self._status = _ActionStatus.CANCEL;
            self._events.trigger('cancel', Array.from(arguments).slice(1), self);
        });

        return this;
    },

    before: function(target, options) {
        target.after(this, options);
        return this;
    },

    delegate: function(delegate) {
        var self = this;

        delegate.onDone(function() {
            self._status = _ActionStatus.DONE;
            self._events.trigger('done', Array.from(arguments).slice(1), self);
        });

        delegate.onFail(function() {
            self._status = _ActionStatus.FAIL;
            self._events.trigger('fail', Array.from(arguments).slice(1), self);
        });

        delegate.onCancel(function() {
            self._status = _ActionStatus.CANCEL;
            self._events.trigger('cancel', Array.from(arguments).slice(1), self);
        });

        return this;
    }
});

creme.component.TimeoutAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._startTimeout, options);
    },

    _startTimeout: function(options) {
        options = $.extend({}, this.options(), options);

        var self = this;
        var delay = options.delay || 0;

        if (delay > 0) {
            window.setTimeout(function() {
                if (self.isRunning()) {
                    self.done(options);
                }
            }, delay);
        } else {
            self.done(options);
        }
    }
});

}(jQuery));
