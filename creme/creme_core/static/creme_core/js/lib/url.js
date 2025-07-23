/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2025  Hybird

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

/* globals HTMLFormElement */

(function() {
"use strict";

function decodeURLSearchData(search) {
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

function decodeURLSearchParams(params) {
    var data = {};

    params.forEach(function(value, key) {
        _.append(data, key, value);
    });

    return data;
}

function toURLSearchParams(data) {
    if (data instanceof URLSearchParams) {
        return data;
    } else if (_.isString(data)) {
        return new URLSearchParams(data);
    }

    var params = new URLSearchParams();

    Object.entries(data || {}).forEach(function(e) {
        var key = e[0], value = e[1];

        if (Array.isArray(value)) {
            if (value.length > 0) {
                value.forEach(function(item) {
                    params.append(key, item);
                });
            }
        } else if (value !== null && value !== undefined) {
            params.append(key, value);
        }
    });

    return params;
}

function toFormData(data) {
    if (data instanceof FormData) {
        return data;
    } else if (data instanceof HTMLFormElement) {
        return new FormData(data);
    } else {
        return assignFormData(new FormData(), data);
    }
}

function assignFormData(params, data) {
    Object.entries(data || {}).forEach(function(e) {
        var key = e[0], value = e[1];

        if (value instanceof Set) {
            value = Array.from(value);
        }

        if (Array.isArray(value)) {
            params.delete(key);

            if (value.length > 0) {
                value.forEach(function(item) {
                    params.append(key, item);
                });
            }
        } else if (value !== null && value !== undefined) {
            params.set(key, value);
        }
    });

    return params;
}

window.RelativeURL = function(url) {
    this._link = document.createElement('a');
    this._link.href = (url instanceof URL) ? url.toString() : url;
};

window.RelativeURL.prototype = {
    _property: function(name, value) {
        if (value === undefined) {
            return this._link[name];
        }

        this._link[name] = value;
        return this;
    },

    href: function(href) {
        return this._property('href', href);
    },

    fullPath: function() {
        return this._link.pathname + this._link.search + this._link.hash;
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
            return this._link.search;
        }

        search = (search instanceof URLSearchParams) ? search.toString() : search;
        this._link.search = search;
        return this;
    },

    hash: function(hash) {
        return this._property('hash', hash);
    },

    properties: function() {
        var url = this._link;

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
            searchData: decodeURLSearchData(url.search),
            hash: url.hash
        };
    },

    searchParams: function(params) {
        if (params === undefined) {
            return new URLSearchParams(this._link.search);
        }

        this._link.search = toURLSearchParams(params).toString();
    },

    searchData: function(data) {
        if (data === undefined) {
            return decodeURLSearchData(this._link.search);
        }

        this._link.search = toURLSearchParams(data).toString();
        return this;
    },

    updateSearchData: function(data) {
        var entries = (data instanceof URLSearchParams) ? decodeURLSearchParams(data) : data;
        var origin = this.searchData();
        var params = toURLSearchParams(Object.assign(origin, entries));

        this._link.search = params.toString();
        return this;
    },

    toString: function() {
        return this._link.toString();
    }
};

_.mixin({
    toRelativeURL: function(url) {
        return new window.RelativeURL(url);
    },
    urlAsDict: function(url) {
        return new window.RelativeURL(url).properties();
    },
    toURLSearchParams: toURLSearchParams,
    decodeURLSearchData: decodeURLSearchData,
    decodeURLSearchParams: decodeURLSearchParams,
    encodeURLSearch: function(data) {
        return _.toURLSearchParams(data).toString();
    },
    // TODO : Move this code to a better place once the refactoring of ajax backend is done
    toFormData: toFormData,
    assignFormData: assignFormData
});

}());
