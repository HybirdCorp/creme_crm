/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2012  Hybird

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

/*
 * CacheBackendEntry
 *
 * contains cached request status and datas.
 */
creme.ajax.CacheBackendEntry = function(key, url, data, dataType, response) {
    this.key = key;
    this.url = url;
    this.data = data;
    this.dataType = dataType;
    this.response = response;
    this.state = undefined;
};


/*
 * CacheBackendCondition
 *
 * base class for cache expiration behaviour.
 */
creme.ajax.CacheBackendCondition = function(cb) {
    this._expired_cb = Object.isFunc(cb) ? cb : function() {return false;};
}

creme.ajax.CacheBackendCondition.prototype = {
    expired: function(entry, options)
    {
        if (entry.state === undefined)
            return true;

        return creme.object.invoke(this._expired_cb, entry, options);
    },

    reset: function(entry) {
        entry.state = {};
    }
}

/*
 * CacheBackendTimeout
 *
 * invalidate cache after a delay in milliseconds.
 */
creme.ajax.CacheBackendTimeout = function(max) {
    this.maxdelay = (max || 0);
}

creme.ajax.CacheBackendTimeout.prototype = new creme.ajax.CacheBackendCondition();
creme.ajax.CacheBackendTimeout.prototype.constructor = creme.ajax.CacheBackendCondition;

$.extend(creme.ajax.CacheBackendTimeout.prototype, {
    expired: function(entry, options)
    {
        if (entry.state === undefined)
            return true;

        var expirationTime = entry.state.time + this.maxdelay;
        return expirationTime <= new Date().getTime();
    },

    reset: function(entry) {
        entry.state = {time: new Date().getTime()};
    }
});



/*
 * CacheBackend
 */

creme.ajax.CacheBackend = function(backend, options) {
    $.extend(this.options, options || {});

    this.delegate = backend || new creme.ajax.Backend();
    this.condition = this.options.condition || new creme.ajax.CacheBackendCondition();
    this.entries  = {};
}

creme.ajax.CacheBackend.prototype = new creme.ajax.Backend();
creme.ajax.CacheBackend.prototype.constructor = creme.ajax.Backend;

$.extend(creme.ajax.CacheBackend.prototype, {
    get: function(url, data, on_success, on_error, options)
    {
        var options = $.extend({}, this.options, options);
        var entry = this._getEntry(url, data, options.dataType)

        this._fetchEntry(entry, on_success, on_error, options);
    },

    _getEntry: function(url, data, dataType)
    {
        var key = $.toJSON([url, dataType, data]);
        return this.entries[key] || new creme.ajax.CacheBackendEntry(key, url, data, dataType);
    },

    _updateEntry: function(entry, response, textStatus)
    {
        entry.response = {data: response, textStatus: textStatus};
        this.condition.reset(entry);
        this.entries[entry.key] = entry;
    },

    _removeEntry: function(entry) {
        delete this.entries[entry.key];
    },

    _fetchEntry: function(entry, on_success, on_error, options)
    {
        var self = this;

        if (!options.forcecache && (this.condition.expired(entry, options) === false)) {
            return creme.object.invoke(on_success, entry.response.data, entry.response.textStatus);
        }

        this.delegate.get(entry.url, entry.data,
                          function(data, textStatus) {
                              self._updateEntry(entry, data, textStatus);
                              creme.object.invoke(on_success, data, textStatus);
                          },
                          function(data, status) {
                              self._removeEntry(entry);
                              creme.object.invoke(on_error, data, status);
                          }, options);
    }
});
