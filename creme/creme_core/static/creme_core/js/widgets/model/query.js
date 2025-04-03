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

creme.model = creme.model || {};

creme.model.AjaxArray = creme.model.Array.sub({
    _init_: function(backend, initial) {
        this.backend(backend);
        this.initial(initial || []);

        this._super_(creme.model.Array, '_init_', this.initial());

        this._queryListeners = {
            done: this._onQueryDone.bind(this),
            fail: this._onQueryError.bind(this),
            cancel: this._onQueryCancel.bind(this)
        };
    },

    _onQueryDone: function(event, data, textStatus) {
        this._events.trigger('fetch-done', [data], this);
        this.patch(data);
    },

    _onQueryCancel: function() {
        this._events.trigger('fetch-cancel', [], this);
    },

    _onQueryError: function(event, data, error) {
        this._events.trigger('fetch-error', [data, error], this);
        this.patch(this.initial());
    },

    initial: function(initial) {
        if (initial === undefined) {
            return Object.isFunc(this._initial) ? this._initial() : this._initial;
        }

        this._initial = initial;
        return this;
    },

    converter: function(converter) {
        return Object.property(this, '_converter', converter);
    },

    backend: function(backend) {
        return Object.property(this, '_backend', backend);
    },

    url: function(url) {
        return Object.property(this, '_url', url);
    },

    cancelFetch: function() {
        if (this._running) {
            if (this._running.isRunning()) {
                this._running.cancel();
            }

            delete this._running;
        }
    },

    fetch: function(data, options, listeners) {
        var url = this.url();
        var query;

        if (Object.isNone(url)) {
            query = new creme.component.Action(function() {
                this.cancel();
            });
        } else {
            query = this.backend().query({action: 'get'})
                                  .data(data || {})
                                  .url(url);

            if (this._converter) {
                query.converter(this._converter);
            }
        }

        this.cancelFetch();

        this._running = query;
        query.one(this._queryListeners)
             .one(listeners || {})
             .start(options);

        return this;
    }
});
}(jQuery));
