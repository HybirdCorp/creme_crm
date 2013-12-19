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

creme.widget.Frame = creme.widget.declare('ui-creme-frame', {

    options: {
        backend:        new creme.ajax.Backend({dataType:'html'}),
        url:            undefined,
        overlay_delay:  100
    },

    _create: function(element, options, cb, sync)
    {
        this._overlay = new creme.dialog.Overlay();
        this._overlay.bind(element)
                     .addClass('frame-loading');

        var frame = this._frame = new creme.dialog.Frame({backend: options.backend});

        frame.on('update', function(event, data, type) {
                  element.trigger('update', [data, statusText]);
              })
             .on('fetch-fail submit-fail', function(event, data, error) {
                  element.trigger('fetch-fail' === event ? 'reloadError' : 'submitError', [data, error]);
              })
             .bind(element)
             .overlayDelay(options.overlay_delay)
             .overlay().addClass('frame-loading');

        element.addClass('widget-ready');

        this.reload(element, undefined, cb);
    },

    url: function(element) {
        return this._lasturl || this.options.url;
    },

    preferredSize: function(element) {
        return creme.layout.preferredSize(element);
    },

    resize: function(element, args) {
        element.trigger('resize', args);
    },

    fill: function(element, data, cb) {
        this._frame.fill(data);
        creme.object.invoke(cb, data);
    },

    reset: function(element, cb)
    {
        this._frame.clear();
        this._lasturl = undefined;
        creme.object.invoke(cb);
    },

    reload: function(element, url, data, listeners)
    {
        var self = this;
        var options = this.options;
        var url = url || this.url();
        var listeners = listeners || {};

        this._lasturl = url;

        if (Object.isNone(url) === false) {
            this._frame.fetch(url, {}, data, listeners);
        }
    },

    submit: function(element, form, listeners)
    {
        var self = this;
        var options = this.options;
        var listeners = listeners || {};
        var url = this.url();

        this._frame.submit(url, {}, form, listeners);
    }
});
