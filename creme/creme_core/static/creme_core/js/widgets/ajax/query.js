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

creme.ajax.Query = creme.component.Action.sub({
    _init_: function(options, backend)
    {
        this._super_(creme.component.Action, '_init_', this._send, options);
        this._backend = backend || new creme.ajax.Backend(options.backend);
        this._converter = function(data) {return data;}
        this._data = {};

        this._onsuccess_cb = $.proxy(this._onBackendSuccess, this);
        this._onerror_cb = $.proxy(this._onBackendError, this);
    },

    _onBackendSuccess: function(data, textStatus)
    {
        try {
            this.done(this._converter(data));
        } catch(e) {
            this.fail(data, e);
        }
    },

    _onBackendError: function(data, error) {
        this.fail(data, error);
    },

    converter: function(converter)
    {
        if (converter === undefined)
            return this;

        if (!Object.isFunc(converter))
            throw Error('converter is not a function');

        this._converter = converter;
        return this;
    },

    backend: function(backend) {
        return Object.property(this, '_backend', backend);
    },

    url: function(url)
    {
        if (url === undefined)
            return Object.isFunc(this._url) ? this._url() : this._url;

        this._url = url;
        return this;
    },

    data: function(data)
    {
        if (data === undefined)
            return Object.isFunc(this._data) ? this._data() : this._data;

        this._data = data;
        return this;
    },

    _send: function(options)
    {
        var options = $.extend({}, this.options(), options || {});

        var data = $.extend({}, this.data() || {}, options.data || {});
        var action = (options.action || 'get').toLowerCase();
        var backend_options = options.backend || {};
        var url = this.url() || '';

        if (Object.isNone(this._backend) || !url)
            return this.cancel();

        if (!Object.isFunc(this._backend[action]))
            throw new Error('no such backend action "%s"'.format(action));

        this._backend[action](url, data, this._onsuccess_cb, this._onerror_cb, backend_options);
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
    var options = options || {};
    return new creme.ajax.Query(options, backend).url(url).data(data || {});
}

