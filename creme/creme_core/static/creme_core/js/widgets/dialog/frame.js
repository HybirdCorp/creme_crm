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

creme.dialog = creme.dialog || {};

creme.dialog.Frame = creme.component.Component.sub({
    _init_: function(options)
    {
        var options = options || {};

        this._overlay = new creme.dialog.Overlay();
        this._overlayDelay = 200;

        this._backend = options.backend || new creme.ajax.Backend({dataType: 'html'});
        this._events = new creme.component.EventHandler();
        this._json = new creme.utils.JSON();
    },

    on: function(event, listener) {
        this._events.on(event, listener);
        return this;
    },

    onUpdate: function(listener) {
        return this.on('update', listener);
    },

    onCleanup: function(listener) {
        return this.on('clear', listener);
    },

    onFetchDone: function(listener) {
        return this.on('fetch-done', listener);
    },

    onFetchFail: function(listener) {
        return this.on('fetch-fail', listener);
    },

    onSubmitDone: function(listener) {
        return this.on('submit-done', listener);
    },

    onSubmitFail: function(listener) {
        return this.on('submit-fail', listener);
    },

    _cleanJSONResponse: function(response)
    {
        var json_matches = response.match('^[\s]*<json>(.*)</json>[\s]*$');
        var json_data = (json_matches !== null && json_matches.length == 2) ? json_matches[1] : undefined;

        if (json_data && this._json.isJSON(json_data)) {
            return {content: json_data, type: 'text/json'};
        }

        return null;
    },

    _cleanResponse: function(response, statusText, dataType)
    {
        var json = this._json;

        if (Object.isType(response, 'string')) {
            return this._cleanJSONResponse(response) || {content: response, type: 'text/html'};
        } else if (Object.isType(response, 'object')) {
            if (response.type == 'text/html') {
                return response;
            } else {
                return {content: response, type: Object.getPrototypeOf(response).jquery ? 'object/jquery' : 'object'};
            }
        }

        return {content: response, type: 'text/html'};
    },

    fill: function(data, action)
    {
        var self = this;
        var data = this._cleanResponse(data);
        var delegate = this._delegate;
        var overlay = this._overlay;

        if (['text/html', 'object/jquery'].indexOf(data.type) === -1)
            return this;

        try {
            overlay.unbind(delegate).update(false);

            this._events.trigger('cleanup', [delegate, action], this);
            delegate.empty();
            overlay.bind(delegate);

            delegate.append($(data.content));
        } catch(e) {
        }

        this._events.trigger('update', [data.content, data.type, action], this);
        return this;
    },

    lastFetchUrl: function() {
        return this._lastFetchUrl;
    },

    clear: function() {
        return this.fill('');
    },

    resize: function(args) {
        this._delegate.trigger('resize', args);
    },

    _formatOverlayContent: function(url, response, error)
    {
        var error_status = error ? error.status : 404;
        var error_message = '<h2>%s&nbsp;(%s)<div class="subtitle">%s</div></h2>' +
                            '<p class="message">%s</p>' + 
                            '<a class="redirect" onclick="creme.utils.reload();">' +
                                gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
                            '</a>';

        return error_message.format(creme.ajax.localizedErrorMessage(error),
                                    error_status,
                                    url,
                                    response)
    },

    fetch: function(url, options, data, listeners)
    {
        var self = this;
        var listeners = listeners || {};
        var query = this._backend.query();
        var overlay = this._overlay;
        var events = this._events;
        var url = url || this.lastFetchUrl();

        events.trigger('before-fetch', [url, options], this);
        overlay.content('')
               .update(true, 'wait', this._overlayDelay);

        query.onDone(function(event, response) {
                  self._lastFetchUrl = url;
                  self.fill(response, 'fetch');
                  events.trigger('fetch-done', [response], this);
              })
             .on('cancel fail', function(event, response, error) {
                  overlay.update(true, error ? error.status : 404, 0)
                         .content(self._formatOverlayContent(url, response, error));
                  events.trigger('fetch-fail', [response, error], this);
              });

        query.one(listeners)
             .url(url || '')
             .get(data, options);
    },

    submit: function(url, options, form, listeners)
    {
        var self = this;
        var url = (form ? (url || form.attr('action')) : url) || this.lastFetchUrl();
        var options = $.extend({action: url}, options || {});
        var listeners = listeners || {};
        var overlay = this._overlay;
        var events = this._events;

        this._events.trigger('before-submit', [form, options], this);

        if (Object.isEmpty(options.action)) {
            overlay.update(true, 404, 0);
            events.trigger('submit-fail', ['', new creme.ajax.XHR({responseText: '', status: 404})], this);
        }

        this._overlay.content('')
                     .update(true, 'wait', this._overlayDelay);

        // TODO : change api in order to force url on submit
        this._backend.submit(form,
                             function(response, statusText, dataType) {
                                 var cleaned = self._cleanResponse(response, statusText, dataType);

                                 self.fill(cleaned.content, 'submit');
                                 events.trigger('submit-done', [cleaned.content, statusText, cleaned.type], this);
                                 creme.object.invoke(listeners.done, 'done', cleaned.content, statusText, cleaned.type);
                             },
                             function(response, error) {
                                 overlay.update(true, error ? error.status : 500, 0)
                                        .content(self._formatOverlayContent(url, response, error));
                                 events.trigger('submit-fail', [response, error], this);
                                 creme.object.invoke(listeners.fail, 'fail', response, error);
                             },
                             options);
    },

    bind: function(delegate)
    {
        if (this._delegate !== undefined)
            throw new Error('frame component is already bound');

        this._delegate = delegate;
        this._overlay.bind(delegate);
        return this;
    },

    unbind: function()
    {
        if (this._delegate === undefined)
            throw new Error('frame component is not bound');

        this._overlay.unbind(delegate);
        this._delegate = undefined;
        return this;
    },

    backend: function(backend) {
        Object.property(this, '_backend', backend);
    },

    delegate: function() {
        return this._delegate;
    },

    overlay: function() {
        return this._overlay;
    },

    overlayDelay: function(delay) {
        return Object.property(this, '_overlayDelay', delay);
    },

    preferredSize: function() {
        return this._delegate ? creme.layout.preferredSize(this._delegate) : {width: 0, height: 0};
    }
});
