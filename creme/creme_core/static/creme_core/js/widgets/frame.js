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

        this._queryReloadListeners = {
            done: function(data, statusText) {
                    self._success_cb(element, data, statusText, cb, 'reloadOk');
                },
            fail: function(data, status) {
                    self._error_cb(element, data, status, error_cb, 'reloadError');
                }
        }

        element.addClass('widget-ready');

        this.reload(element, undefined, cb);
    },

    _update: function(element, data)
    {
        this._overlay.unbind(element);
        this._overlay.update(false);

        creme.widget.destroy(element.children());
        element.empty();
        this._overlay.bind(element);

        try {
            element.append($(data));
            creme.widget.ready(element);
        } catch(e) {
        }
    },

    _clean_json: function(element, data)
    {
        var json_matches = data.match('^[\s]*<json>(.*)</json>[\s]*$');
        var json = (json_matches !== null && json_matches.length == 2) ? json_matches[1] : undefined;

        if (new creme.utils.JSON().isJSON(json)) {
            return [json, 'text/json'];
        }
    },

    _clean_data: function(element, data)
    {
        var dataType = typeof data;

        if (dataType === 'string') {
            return this._clean_json(element, data) || [data, 'text/html'];
        }

        if (dataType === 'object') {
            return [data, Object.getPrototypeOf(data).jquery ? 'object/jquery' : 'object'];
        }

        return [data, dataType];
    },

    _success_cb: function(element, data, statusText, cb, trigger)
    {
        var self = this;
        var cleaned = self._clean_data(element, data);
        var data = cleaned[0];
        var dataType = cleaned[1];

        // if guessed data is html, replace content of frame
        if (dataType === 'text/html' || dataType === 'object/jquery')
            self._update(element, data);

        creme.object.invoke(cb, data, statusText, dataType);
        element.trigger(trigger, [data, statusText]);
    },

    _error_cb: function(element, data, status, cb, trigger)
    {
        this._overlay.update(true, status.status, 0);
        creme.object.invoke(cb, data, status);
        element.trigger(trigger, [data, status]);
    },
    
    preferredSize: function(element)
    {
        var height = 0;
        var width = 0;

        $('> *', element).each(function() {
            width = Math.max(width, $(this).position().left + $(this).outerWidth());
            height = Math.max(height, $(this).position().top + $(this).outerHeight());
        });

        return [Math.round(width), Math.round(height)];
    },

    resize: function(element, args) {
        element.trigger('resize', args);
    },

    fill: function(element, data, cb) {
        this._success_cb(element, data, '', cb, 'reloadOk');
        this._lasturl = undefined;
    },

    reset: function(element, cb) {
        this._success_cb(element, '', '', cb, 'reloadOk');
        this._lasturl = undefined;
    },

    reload: function(element, url, data, listeners)
    {
        var self = this;
        var options = this.options;
        var url = url || this.url();
        var listeners = listeners || {};

        if (creme.object.isnone(url)) {
            this.reset(element, listeners.done);
            return;
        }

        element.trigger('beforeReload', [url]);

        this._overlay.update(true, 'wait', options.overlay_delay);
        this._lasturl = url;

        options.backend.get(url, data, 
                            function(data, statusText) {
                                self._success_cb(element, data, statusText, listeners.done, 'reloadOk');
                            },
                            function(data, status) {
                                self._error_cb(element, data, status, listeners.fail, 'reloadError');
                            });
    },

    url: function(element) {
        return this._lasturl || this.options.url;
    },

    submit: function(element, form, listeners)
    {
        var self = this;
        var options = this.options;
        var listeners = listeners || {};
        var url = this.url();

        this._overlay.update(true, 'wait', options.overlay_delay);

        element.trigger('beforeSubmit', [form]);

        form.attr('action', form.attr('action') || url);

        options.backend.submit(form, 
                               function(data, statusText) {
                                   self._success_cb(element, data, statusText, listeners.done, 'submitOk');
                               },
                               function(data, status) {
                                   self._error_cb(element, data, status, listeners.fail, 'submitError');
                               });
    }
});
