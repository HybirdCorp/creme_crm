/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2013  Hybird

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

creme.component.Action = creme.component.Component.sub({
    _init_: function(action, options)
    {
        this._events = new creme.component.EventHandler();
        this._options = options || {};
        this._status = 'done';
        this._action = Object.isFunc(action) ? action : this.done;
    },

    start: function()
    {
        var self = this;

        if (this.isRunning() === true)
            return this;

        try {
            this._events.trigger('start', Array.copy(arguments), this);
            this._status = 'run';
            this._action.apply(this, Array.copy(arguments));
        } catch(e) {
            this.fail(e);
        }

        return this;
    },

    done: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'done';
        this._events.trigger('done', Array.copy(arguments), this);
        return this;
    },

    fail: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'fail';
        this._events.trigger('fail', Array.copy(arguments), this);
        return this;
    },

    cancel: function()
    {
        if (this.isRunning() === false)
            return this;

        this._status = 'cancel';
        this._events.trigger('cancel', Array.copy(arguments), this);
        return this;
    },

    trigger: function(event)
    {
        this._events.trigger(event, Array.copy(arguments).slice(1), this);
        return this;
    },

    action: function(data)
    {
        var self = this;
        var action = (data === undefined || Object.isFunc(data)) ? data : function() {self.done(data);};

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
        return this._status === 'run';
    },

    status: function() {
        return this._status;
    },

    options: function(options) {
        return Object.property(this, '_options', options);
    },

    after: function(source)
    {
        var self = this;

        source.onDone(function(event, data) {
            self.start(data);
        });

        source.onFail(function(event, data) {
            self.fail(data);
        });

        source.onCancel(function(event, data) {
            self.cancel(data);
        });

        return this;
    }
});


creme.component.TimeoutAction = creme.component.Action.sub({
    _init_: function(options) {
        this._super_(creme.component.Action, '_init_', this._startTimeout, options);
    },

    _startTimeout: function(options)
    {
        var self = this;
        var delay = options.delay;

        if (delay) {
            window.setTimeout(function() {
                if (self.isRunning()) {
                    self.done(options);
                }
            }, delay);
        } else {
            this.done(0);
        }
    }
});
