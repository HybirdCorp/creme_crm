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
        url:            '',
        overlay_delay:  100
    },

    _create: function(element, options, cb, sync)
    {
        var overlay = this._create_overlay(element, options);

        element.append(overlay);
        element.addClass('widget-ready');

        this.reload(element, undefined, cb);
    },

    _update: function(element, data)
    {
        var overlay = $('> .ui-creme-overlay', element);

        element.empty();
        element.append(overlay);

        try {
            element.append($(data));
            creme.widget.ready(element);
        } catch(e) {
        }
    },

    _overlay_state: function(element, visible, status)
    {
    	var visible = visible || false;
        var options = this.options;
        var overlay = $('> .ui-creme-overlay', element);
        var z_index = visible ? 1 : -1;

        overlay.css('z-index', z_index).toggleClass('overlay-active', visible || false);

        if (status === undefined)
            overlay.removeAttr('status');
        else
            overlay.attr('status', status);
    },

    _clean_json: function(element, data)
    {
        var json_matches = data.match('^[\s]*<json>(.*)</json>[\s]*$');
        var json = (json_matches !== null && json_matches.length == 2) ? json_matches[1] : undefined;

        if (creme.ajax.json.parse(json) !== null)
            return [json, 'text/json'];
    },

    _clean_data: function(element, data) {
        return this._clean_json(element, data) || [data, 'text/html'];
    },

    _success_cb: function(element, data, statusText, cb)
    {
        var self = this;
        var cleaned = self._clean_data(element, data);
        var data = cleaned[0];
        var dataType = cleaned[1];

        //console.log('reload done', data, dataType);

        // if guessed data is html, replace content of frame
        if (dataType === 'text/html')
            self._update(element, data);

        creme.object.deferred_cancel(element, 'overlay');
        self._overlay_state(element, false);

        creme.object.invoke(cb, data, statusText, dataType);
    },

    _error_cb: function(element, data, status, cb)
    {
        //console.log('reload failed', this.options, status);

        var self = this;

        creme.object.deferred_cancel(element, 'overlay');
        self._overlay_state(element, true, status.status);

        creme.object.invoke(cb, data, status);
    },

    fill: function(element, data) {
        this._success_cb(element, data);
    },

    reload: function(element, url, cb, error_cb)
    {
        var self = this;
        var options = this.options;
        var url = (url === undefined) ? options.url : url;

        creme.object.deferred_start(element, 'overlay', function() {self._overlay_state(element, true, 'wait');}, options.overlay_delay);
        options.url = url;

        options.backend.get(url, {},
                            function(data, statusText) {
                                self._success_cb(element, data, statusText, cb);
                                element.trigger('reloadOk', [data, statusText]);
                            },
                            function(data, status) {
                                self._error_cb(element, data, status, error_cb);
                                element.trigger('reloadError', [data, status]);
                            })
    },

    submit: function(element, form, cb, error_cb)
    {
        var self = this;
        var options = this.options;

        creme.object.deferred_start(element, 'overlay', function() {self._overlay_state(element, true, 'wait');}, options.overlay_delay);

        options.backend.submit(form,
                               function(data, statusText) {
                                   self._success_cb(element, data, statusText, cb);
                                   element.trigger('submitOk', [data, statusText]);
                               },
                               function(data, status) {
                                   self._error_cb(element, data, status, error_cb);
                                   element.trigger('submitError', [data, status]);
                               });
    },

    _create_overlay: function(element, options)
    {
        var overlay = $('<div/>').addClass('ui-creme-overlay').css('z-index', -1);
        return overlay;
    }
});
