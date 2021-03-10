/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2018-2021  Hybird

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

var __decodeSearchData = creme.ajax.decodeSearchData = function(search) {
    search = search.replace(/^\?/, '');

    var searchData = {};

    if (search) {
        var query = search.split('&');

        query.forEach(function(e) {
            var item = e.split('=');
            var key = decodeURIComponent(item[0]);
            var value = decodeURIComponent(item[1]);
            var entry = searchData[key];

            if (entry === undefined) {
                entry = value;
            } else if (Array.isArray(entry)) {
                entry.push(value);
            } else {
                entry = [entry, value];
            }

            searchData[key] = entry;
        });
    }

    return searchData;
};

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
        return '${pathname}${search}${hash}'.template(this._parser);
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
        if (search === undefined) {
            return this._parser.search;
        }

        this._parser.search = search;
        this._searchData = __decodeSearchData(search);
        return this;
    },

    hash: function(hash) {
        return this._property('hash', hash);
    },

    properties: function() {
        return {
            href: this.href(),
            username: this.username(),
            password: this.password(),
            protocol: this.protocol(),
            host: this.host(),
            hostname: this.hostname(),
            port: this.port(),
            pathname: this.pathname(),
            search: this.search(),
            searchData: this.searchData(),
            hash: this.hash()
        };
    },

    searchData: function(data) {
        if (data === undefined) {
            return this._searchData;
        }

        this.search(creme.ajax.param(data));
        return this;
    },

    updateSearchData: function(data) {
        data = data || {};
        return this.searchData($.extend({}, this._searchData, data));
    },

    toString: function() {
        return this._parser.toString();
    }
});

creme.ajax.parseUrl = function(url) {
    var parser = document.createElement('a');

    parser.href = url;

    return {
        href: parser.href,
        username: parser.username,
        password: parser.password,
        protocol: parser.protocol,
        host: parser.host,
        hostname: parser.hostname,
        port: parser.port,
        pathname: parser.pathname,
        search: parser.search,
        searchData: __decodeSearchData(parser.search),
        hash: parser.hash
    };
};

creme.ajax.param = function(data) {
    return $.param(data, jQuery.ajaxSettings.traditional);
};

}(jQuery));
