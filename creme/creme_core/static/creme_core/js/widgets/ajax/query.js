/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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

creme.ajax = creme.ajax || {};

creme.ajax.Query = creme.component.Action.sub({
    _init_: function(options, backend) {
        this._super_(creme.component.Action, '_init_', this._send, options);
        this._backend = backend || creme.ajax.defaultBackend();
        this._converter = function(data) { return data; };
        this._data = {};
        this._cancellable = false;

        this._successCb = this._onBackendSuccess.bind(this);
        this._errorCb = this._onBackendError.bind(this);
    },

    _onBackendSuccess: function(data, textStatus, xhr) {
        if (this.isRunning()) {
            try {
                this.done(this._converter(data), xhr);
            } catch (e) {
                this.fail(data, e);
            }
        }
    },

    _onBackendError: function(data, error) {
        this.fail(data, error);
    },

    converter: function(converter) {
        if (converter === undefined) {
            return this._converter;
        }

        if (!Object.isFunc(converter)) {
            throw Error('converter is not a function');
        }

        this._converter = converter;
        return this;
    },

    isCancelable: function() {
        return this.isRunning() && this._cancelable;
    },

    cancel: function() {
        if (this.isCancelable() === false) {
            throw new Error('unable to cancel this query');
        }

        return this._super_(creme.component.Action, 'cancel');
    },

    backend: function(backend) {
        return Object.property(this, '_backend', backend);
    },

    url: function(url) {
        if (url === undefined) {
            return Object.isFunc(this._url) ? this._url() : this._url;
        }

        this._url = url;
        return this;
    },

    data: function(data) {
        if (data === undefined) {
            return Object.isFunc(this._data) ? this._data() : this._data;
        }

        this._data = data;
        return this;
    },

    _send: function(options) {
        options = $.extend(true, {}, this.options(), options || {});

        var data = $.extend({}, this.data() || {}, options.data || {});
        var action = (options.action || 'get').toLowerCase();
        var backendOptions = options.backend || {};
        var url = this.url() || '';

        try {
            if (Object.isNone(this._backend)) {
                throw new Error('Missing ajax backend');
            }

            if (!Object.isFunc(this._backend[action])) {
                throw new Error('Missing ajax backend action "%s"'.format(action));
            }

            if (Object.isEmpty(url)) {
                throw new Error('Unable to send request with empty url');
            }

            this._cancelable = (action === 'get');
            this._backend[action](url, data, this._successCb, this._errorCb, backendOptions);
        } catch (e) {
            var message = e.message || String(e);
            this.fail(e, new creme.ajax.AjaxResponse(400, message));
        }

        return this;
    },

    get: function(data, options) {
        return this.start({action: 'get', data: data, backend: options || {}});
    },

    post: function(data, options) {
        return this.start({action: 'post', data: data, backend: options || {}});
    }
});

creme.ajax.query = function(url, options, data, backend) {
    options = options || {};
    return new creme.ajax.Query(options, backend).url(url || '').data(data || {});
};
}(jQuery));
