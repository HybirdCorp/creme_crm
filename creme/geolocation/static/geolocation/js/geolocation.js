/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2014-2025  Hybird

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

creme.geolocation = creme.geolocation || {};

creme.geolocation.LocationStatus = {
    UNDEFINED: 0,
    MANUAL:    1,
    PARTIAL:   2,
    COMPLETE:  3
};

creme.geolocation.locationStatusLabel = function(status) {
    switch (status) {
        case creme.geolocation.LocationStatus.UNDEFINED:
            return gettext("Not localized");
        case creme.geolocation.LocationStatus.MANUAL:
            return gettext("Manual location");
        case creme.geolocation.LocationStatus.PARTIAL:
            return gettext("Partially matching location");
        default:
            return '';
    }
};

creme.geolocation.Location = creme.component.Component.sub({
    _init_: function(options) {
        options = options || {};

        if (options instanceof creme.geolocation.Location) {
            return this._init_(options.props());
        }

        this.id(options.id);
        this.content(options.content || '');
        this.title(options.title || '');
        this.owner(options.owner);
        this.icon(options.icon);
        this.iconShadow(options.iconShadow);
        this.extraData(options.extraData);

        if (options.latitude) {
            this.position({lat: options.latitude, lng: options.longitude});
        } else {
            this.position(options.position || null);
        }

        this.visible(options.visible || false);
        this.status(options.status || creme.geolocation.LocationStatus.UNDEFINED);
        this.url(options.url);
    },

    props: function() {
        return {
            id: this.id(),
            content: this.content(),
            title: this.title(),
            owner: this.owner(),
            position: this.position(),
            visible: this.visible(),
            status: this.status(),
            url: this.url(),
            icon: this.icon(),
            iconShadow: this.iconShadow(),
            extraData: this.extraData()
        };
    },

    extraData: function(extra) {
        return Object.property(this, '_extraData', extra);
    },

    icon: function(icon) {
        return Object.property(this, '_icon', icon);
    },

    iconShadow: function(icon) {
        return Object.property(this, '_iconShadow', icon);
    },

    id: function(id) {
        return Object.property(this, '_id', id);
    },

    content: function(content) {
        return Object.property(this, '_content', content);
    },

    title: function(title) {
        return Object.property(this, '_title', title);
    },

    owner: function(owner) {
        return Object.property(this, '_owner', owner);
    },

    position: function(position) {
        return Object.property(this, '_position', position);
    },

    visible: function(visible) {
        return Object.property(this, '_visible', visible);
    },

    status: function(status) {
        return Object.property(this, '_status', status);
    },

    url: function(url) {
        return Object.property(this, '_url', url);
    },

    isComplete: function() {
        return this.status() === creme.geolocation.LocationStatus.COMPLETE;
    },

    isPartial: function() {
        return this.status() === creme.geolocation.LocationStatus.PARTIAL;
    },

    isManual: function() {
        return this.status() === creme.geolocation.LocationStatus.MANUAL;
    },

    hasPosition: function() {
        return Object.isEmpty(this._position) === false;
    },

    statusLabel: function() {
        return creme.geolocation.locationStatusLabel(this._status);
    },

    positionLabel: function() {
        return this.hasPosition() ? '%3.6f, %3.6f'.format(this._position.lat, this._position.lng) : '';
    },

    markerLabel: function() {
        // An address is typically shown as
        // - owner: the creme entity (e.g. its name) this address belongs to
        // - content: the actual street/city/etc information
        // - title: the localized label for billing/shipping addresses (most of the time),
        //          or a user-defined title for additional addresses

        var title = this.title();
        if (Object.isNotEmpty(title)) {
            // If there's a title, it's usually less important than the actual address information,
            // so we show it in parentheses.
            title = "(" + title + ")";
        }
        return [
            this.owner() || '',
            this.content(),
            title
        ].filter(Object.isNotEmpty).join('\n');
    }
});

creme.geolocation.GeoMapController = creme.component.Component.sub({
    _init_: function (options) {
        options = $.extend({
            allowGeocoder: true
        }, options || {});

        this._events = new creme.component.EventHandler();
        this._enabled = false;
        this._allowGeocoder = options.allowGeocoder;
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
        return this;
    },

    trigger: function(event, data) {
        if (this.isBound()) {
            this._element.trigger('geomap-' + event, [this].concat(data || []));
        }

        this._events.trigger(event, data, this);
        return this;
    },

    bind: function(element) {
        if (this.isBound()) {
            throw new Error('GeoMapController is already bound');
        }

        this._element = element;
        this._bindMap(element);

        return this;
    },

    unbind: function() {
        if (!this.isBound()) {
            throw new Error('GeoMapController is not bound');
        }

        this._unbindMap(this._element);
        this._element = undefined;
    },

    element: function() {
        return this._element;
    },

    isBound: function() {
        return Object.isNone(this._element) === false;
    },

    isGeocoderAllowed: function(allowed) {
        return Object.property(this, '_allowGeocoder', allowed);
    },

    isMapEnabled: function() {
        return false;
    },

    isGeocoderEnabled: function() {
        return false;
    },

    _bindMap: function(element) {
        throw new Error('Not implemented');
    },

    _unbindMap: function(element) {
        throw new Error('Not implemented');
    },

    markLocation: function(options, listeners) {
        options = options || {};

        var self = this;
        var location = new creme.geolocation.Location(options.location);
        var query;

        if (location.hasPosition() && !options.force) {
            query = new creme.component.Action(function() {
                this.done(
                    location.position(),
                    location.status(),
                    {}
                );
            });
        } else {
            query = this._searchLocationQuery(location.content());
        }

        query.onDone(function(event, position, status, data) {
                  self._updateLocationMarker({
                      id: location.id(),
                      title: location.markerLabel(),
                      location: location,
                      position: position,
                      status: status,
                      icon: location.icon(),
                      iconShadow: location.iconShadow(),
                      draggable: options.draggable || false,
                      searchData: data,
                      extraData: options.extraData || {}
                  });
              })
             .on(listeners || {});

        return query.start();
    },

    _updateLocationMarker: function(options) {
        options = options || {};
        var marker = this.updateOrAddMarker(options.id, options);
        this.trigger('marker-move', [
            marker,
            Object.assign(this.getMarkerProperties(options.id), {
                status: options.status,
                searchData: options.searchData,
                location: options.location
            })
        ]);
    },

    _searchLocationQuery: function(content) {
        return new creme.component.Action(function() {
            this.cancel();
        });
    },

    isEnabled: function(enabled) {
        if (enabled === undefined) {
            return this._enabled || false;
        }

        this._enabled = enabled;
        this.trigger('status', enabled);
        this.trigger('status-${state}'.template({
            state: enabled ? 'enabled' : 'disabled'
        }));
    },

    updateOrAddMarker: function(id, options) {
        if (this.hasMarker(id)) {
            this.updateMarker(id, options);
            return this.getMarker(id);
        } else {
            return this.addMarker(id, options);
        }
    },

    replaceMarkers: function(data) {
        data = (data || []).filter(function(d) { return Object.isNotEmpty(d.id); });

        var dataIds = data.map(function(d) { return d.id; });
        var markerIds = this.markerIds();

        data.map(function(data) {
            return this.updateOrAddMarker(data.id, data);
        }.bind(this));

        var removed = markerIds.filter(function(id) {
            return dataIds.indexOf(id) === -1;
        });

        removed.forEach(this.removeMarker.bind(this));

        return this.markers();
    },

    addMarker: function(id, options) {
        throw new Error('Not implemented');
    },

    removeMarker: function(id) {
        return this;
    },

    removeAllMarkers: function() {
        this.markerIds().forEach(this.removeMarker.bind(this));
        return this;
    },

    updateMarker: function(id, options) {
        return this;
    },

    getMarker: function(id) {
        throw new Error('Not implemented');
    },

    getMarkerProperties: function(id) {
        throw new Error('Not implemented');
    },

    hasMarker: function(id) {
        return false;
    },

    markers: function(query) {
        return [];
    },

    markerIds: function(query) {
        return [];
    },

    toggleMarker: function(id, state) {
        return this;
    },

    toggleAllMarkers: function(state) {
        return this;
    },

    addShape: function(id, options) {
        throw new Error('Not implemented');
    },

    getShape: function(id) {
        throw new Error('Not implemented');
    },

    hasShape: function(id) {
        return false;
    },

    updateOrAddShape: function(id, options) {
        if (this.hasShape(id)) {
            this.updateShape(id, options);
            return this.getShape(id);
        } else {
            return this.addShape(id, options);
        }
    },

    updateShape: function(id, options) {
        return this;
    },

    removeShape: function(id) {
        return this;
    },

    removeAllShapes: function() {
        this.shapeIds().forEach(this.removeShape.bind(this));
        return this;
    },

    shapes: function(query) {
        return [];
    },

    shapeIds: function(query) {
        return [];
    },

    autoResize: function() {
        return this;
    },

    adjustMap: function() {
        throw new Error('Not implemented');
    },

    adjustMapToShape: function(id) {
        throw new Error('Not implemented');
    }
});

}(jQuery));
