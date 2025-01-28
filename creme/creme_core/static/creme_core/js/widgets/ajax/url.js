/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018-2025  Hybird

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

function __decodeSearchData(search) {
    search = search.replace(/^\?/, '');

    var searchData = {};

    if (search) {
        var query = search.split('&');

        query.forEach(function(e) {
            var item = e.split('=');
            var key = decodeURIComponent(item[0]);
            var value = decodeURIComponent(item[1]);

            _.append(searchData, key, value);
        });
    }

    return searchData;
};

function __decodeURLSearchParams(params) {
    var data = {};

    params.forEach(function(value, key) {
        _.append(data, key, value);
    });

    return data;
}

creme.ajax.URL = creme.component.Component.sub({
    _init_: function(url) {
        this._parser = document.createElement('a');
        this._parser.href = url;
        this._searchData = __decodeSearchData(this._parser.search);
    },

    _property: function(name, value) {
        if (value === undefined) {
            return this._parser[name];
        }

        this._parser[name] = value;
        return this;
    },

    href: function(href) {
        return this._property('href', href);
    },

    relativeUrl: function() {
        return this._parser.pathname + this._parser.search + this._parser.hash;
    },

    username: function(username) {
        return this._property('username', username);
    },

    password: function(password) {
        return this._property('password', password);
    },

    protocol: function(protocol) {
        return this._property('protocol', protocol);
    },

    host: function(host) {
        return this._property('host', host);
    },

    hostname: function(hostname) {
        return this._property('hostname', hostname);
    },

    port: function(port) {
        return this._property('port', port);
    },

    pathname: function(pathname) {
        return this._property('pathname', pathname);
    },

    search: function(search) {
        return this._property('search', this);
    },

    hash: function(hash) {
        return this._property('hash', hash);
    },

    properties: function() {
        var url = this._parser;

        return {
            href: url.href,
            username: url.username,
            password: url.password,
            protocol: url.protocol,
            host: url.host,
            hostname: url.hostname,
            port: url.port,
            pathname: url.pathname,
            search: url.search,
            searchData: __decodeSearchData(url.search),
            hash: url.hash
        };
    },

    searchData: function(data) {
        if (data === undefined) {
            return __decodeSearchData(this._url.search);
        }

        data = (data instanceof URLSearchParams) ? data : new URLSearchParams(data);
        this._parser.search = data.toString();
        return this;
    },

    updateSearchData: function(data) {
        var entries = (data instanceof URLSearchParams) ? __decodeURLSearchParams(data) : data;
        var origin = __decodeSearchData(this._parser.search);
        var params = new URLSearchParams(Object.assign(origin, entries));

        this._url.search = params.toString();
        return this;
    },

    toString: function() {
        return this._parser.toString();
    }
});

creme.ajax.parseUrl = function(url) {
    var parser = document.createElement('a');

    parser.href = url;

    return {
        href: url.href,
        username: url.username,
        password: url.password,
        protocol: url.protocol,
        host: url.host,
        hostname: url.hostname,
        port: url.port,
        pathname: url.pathname,
        search: url.search,
        searchData: __decodeSearchData(url.params),
        hash: url.hash
    };
};

creme.ajax.param = function(data) {
    // Use explicit traditional=true argument to replace ajaxSettings.traditional deprecated
    // since jQuery 1.9 see (https://bugs.jquery.com/ticket/12137)
    // return $.param(data, jQuery.ajaxSettings.traditional);
    // return $.param(data, true);
    return (new URLSearchParams(data)).toString();
};

creme.ajax.decodeSearchData = __decodeSearchData;

}(jQuery));
