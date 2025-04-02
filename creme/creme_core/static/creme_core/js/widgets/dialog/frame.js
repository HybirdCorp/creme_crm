/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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
 * Requires : creme.utils
 */

(function($) {
"use strict";

creme.dialog = creme.dialog || {};

creme.dialog.FrameContentData = creme.component.Component.sub({
    _init_: function(content, dataType) {
        var cleaned = {};

        if (Object.isNone(content)) {
            cleaned = {content: '', type: 'text/plain'};
        } else if (creme.dialog.FrameContentData.prototype.isPrototypeOf(content)) {  /* frame content data */
            cleaned = {
                content: content.content,
                type: content.type,
                data: content._cleanedData
            };
        } else if (Object.isString(content)) {    /* text data with content-type */
            switch (dataType) {
                case 'text/plain':
                    cleaned = {content: String(content), type: dataType}; break;
                case 'html':
                case 'text/html':
                    cleaned = this._cleanPRE(content);

                    // ok... not html, just plain text with <pre></pre>
                    if (cleaned.type === 'text/plain') {
                        // guess if it is json after all
                        try {
                            cleaned = this._cleanJSON(cleaned.content, dataType);
                        } catch (e) {}
                    } else {
                        cleaned = this._cleanHTML(content, dataType);
                    }

                    break;
                case 'text/json':
                case 'text/javascript':
                case 'application/json':
                case 'application/javascript':
                    cleaned = this._cleanPRE(content, 'text/plain');

                    try {
                        cleaned = this._cleanJSON(cleaned.content, dataType);
                    } catch (e) {}

                    break;
                default:
                    cleaned = this._cleanPRE(content);

                    try {
                        cleaned = this._cleanJSON(cleaned.content);
                    } catch (e) {
                        if (!cleaned.type) {
                            cleaned = this._cleanHTML(cleaned.content);
                        }
                    }

                    console.warn('[frame] unrecognized content-type "%s"... guessed as "%s"'.format(dataType, cleaned.type));
            }
        } else if (Object.getPrototypeOf(content).jquery) {  /* jQuery object */
            cleaned = {content: content, type: 'object/jquery'};
        } else if (Object.isType(content, 'object')) {
            cleaned = {content: content, type: 'object'};
        } else {
            cleaned = {content: Object.isNone(content) ? '' : String(content), data: content, type: 'text/plain'};
        }

        this.content = cleaned.content;
        this.type = cleaned.type;
        this._cleanedData = cleaned.data;
    },

    _cleanPRE: function(content, dataType) {
        // Some browsers (like firefox) wrap empty/invalid html text with <pre> tag
        // The latest versions of google chrome (at least > 123, maybe sooner) are adding an extra
        // <div class="{guessed-contentype}-formatter-container"></div>
        var matches = content.match(new RegExp('^[\\s]*<pre[^>]*>([^<]*)</pre>.*$'));

        if (matches !== null && matches.length === 2) {
            return {content: matches[1], type: 'text/plain'};
        }

        return {content: content, type: dataType};
    },

    _cleanJSON: function(content, dataType) {
        try {
            return {content: content, data: JSON.parse(content), type: 'text/json'};
        } catch (e) {
            if (dataType) {
                console.warn('[frame] received invalid JSON data with content-type "%s"'.format(dataType), e);
            }

            throw e;
        }
    },

    _cleanWrappedJSON: function(content, dataType) {
        var matches = content.match(new RegExp('^[\\s]*<json>(.*)</json>[\\s]*$', 'i'));

        if (matches !== null && matches.length === 2) {
            try {
                return this._cleanJSON(matches[1]);
            } catch (e) {}
        }

        return {content: content, type: dataType};
    },

    _cleanHTML: function(content, dataType) {
        // Handle <json> tag (IE)
        var cleaned = this._cleanWrappedJSON(content, dataType);

        // if discovered another datatype ... like text/json.. return result.
        if (cleaned.type === 'text/json') {
            return cleaned;
        }

        // Convert to DOM element or assume it is plain text.
        try {
            // upgrade to Jquery 1.9x : html content without starting '<' is no longer supported.
            //                          use $.trim() for trailing space or returns.
            return {content: content, data: $(content.trim()), type: 'text/html'};
        } catch (e) {
            if (dataType) {
                console.warn('[frame] received invalid HTML with content-type "%s": '.format(dataType), e);
            }

            return {content: content, type: 'text/plain'};
        }
    },

    data: function() {
        return this._cleanedData || this.content;
    },

    isEmpty: function() {
        return Object.isEmpty(this.data());
    },

    isPlainText: function() {
        return this.type === 'text/plain';
    },

    isJSONOrObject: function() {
        return ['application/json', 'text/json', 'object'].indexOf(this.type) !== -1;
    },

    isHTMLOrElement: function() {
        return creme.utils.isHTMLDataType(this.type) || (this.type === 'object/jquery');
    },

    isHTML: function() {
        return creme.utils.isHTMLDataType(this.type);
    }
});

creme.dialog.Frame = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            autoActivate: true,
            overlayDelay: 200,
            fillOnError: false
        }, options || {});

        this._overlay = new creme.dialog.Overlay();
        this._overlayDelay = options.overlayDelay;
        this._contentReady = false;
        this._fillOnError = options.fillOnError;

        this._backend = options.backend || creme.ajax.defaultBackend();
        this._events = new creme.component.EventHandler();
        this._autoActivate = options.autoActivate;
    },

    on: function(event, listener) {
        this._events.on(event, listener);
        return this;
    },

    onUpdate: function(listener) {
        return this.on('update', listener);
    },

    onCleanup: function(listener) {
        return this.on('cleanup', listener);
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

    _cleanResponse: function(response, dataType) {
        return new creme.dialog.FrameContentData(response, dataType);
    },

    deactivateContent: function() {
        if (this._contentReady) {
            creme.widget.shutdown(this._delegate);
            this._contentReady = false;
        }
    },

    activateContent: function() {
        if (!this._contentReady) {
            creme.widget.ready(this._delegate);
            this._contentReady = true;
        }
    },

    isContentReady: function() {
        return this._contentReady;
    },

    fill: function(data, action) {
        data = this._cleanResponse(data, 'text/html');

        var delegate = this._delegate;
        var overlay = this._overlay;

        if (!data.isHTMLOrElement()) {
            return this;
        }

        try {
            overlay.unbind(delegate).update(false);

            this._events.trigger('cleanup', [delegate, action], this);
            this.deactivateContent();

            delegate.empty();
            overlay.bind(delegate);

            var content = data.data();

            if (content.length > 0) {
                delegate.append(content);

                if (this._autoActivate) {
                    this.activateContent();
                }
            }
        } catch (e) {
            console.error(e);
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

    _cleanErrorResponse: function(url, response, error) {
        var status = error ? error.status : 404;
        var cleaned = this._cleanResponse(response, "text/html");

        if (cleaned.isHTMLOrElement() && !cleaned.isEmpty()) {
            return cleaned;
        } else {
            return this._cleanResponse((
                '<h2>${statusMessage}&nbsp;(${status})<div class="subtitle">${url}</div></h2>' +
                '<p class="message">${message}</p>' +
                '<a class="redirect" onclick="creme.utils.reload();">' +
                    gettext('Reload the page or click here. If the problem persists, please contact your administrator.') +
                '</a>'
            ).template({
                statusMessage: creme.ajax.localizedErrorMessage(error),
                status: status,
                url: url,
                message: response || ''
            }), "text/html");
        }
    },

    fetch: function(url, options, data, listeners) {
        var self = this;

        listeners = listeners || {};
        url = url || this.lastFetchUrl();

        var query = this._backend.query();
        var overlay = this._overlay;
        var events = this._events;

        events.trigger('before-fetch', [url, options], this);
        overlay.content('')
               .update(true, 'wait', this._overlayDelay);

        query.onDone(function(event, response) {
                  self._lastFetchUrl = url;
                  self.fill(response, 'fetch');
                  events.trigger('fetch-done', [response], this);
              })
             .on('cancel fail', function(event, response, error) {
                 var errorStatus = error ? error.status : 404;
                 var errorContent = self._cleanErrorResponse(url, response, error);

                 if (self._fillOnError) {
                     self.fill(errorContent, 'fetch');
                 } else {
                     overlay.update(true, errorStatus, 0)
                            .content(errorContent.data());
                 }

                 events.trigger('fetch-fail', [response, error], this);
              });

        query.one(listeners)
             .url(url || '')
             .get(data, options);

        return this;
    },

    submit: function(url, options, form, listeners) {
        var self = this;

        url = (form ? (url || form.attr('action')) : url) || this.lastFetchUrl();
        options = $.extend({action: url}, options || {});
        listeners = listeners || {};

        var overlay = this._overlay;
        var events = this._events;

        this._events.one(listeners);
        this._events.trigger('before-submit', [form, options], this);

        if (Object.isEmpty(options.action)) {
            overlay.update(true, 404, 0);
            events.trigger('submit-fail', ['', new creme.ajax.XHR({responseText: '', status: 404})], this);
            return this;
        }

        this._overlay.content('')
                     .update(true, 'wait', this._overlayDelay);

        // TODO : change api in order to force url on submit
        this._backend.submit(form,
                             function(response, statusText, xhr) {
                                 var dataType = xhr.getResponseHeader('Content-Type').split(';')[0];
                                 var cleaned = self._cleanResponse(response, dataType);

                                 if (cleaned.isHTMLOrElement()) {
                                     self.fill(cleaned, 'submit');
                                 }

                                 events.trigger('submit-done', [cleaned, cleaned.type], this);
                             },
                             function(response, error) {
                                 var errorStatus = error ? error.status : 500;
                                 var errorContent = self._cleanErrorResponse(url, response, error);

                                 if (self._fillOnError) {
                                     self.fill(errorContent, 'submit');
                                 } else {
                                     overlay.update(true, errorStatus, 0)
                                            .content(errorContent.data());
                                 }

                                 events.trigger('submit-fail', [response, error], this);
                             },
                             options);

        return this;
    },

    isBound: function() {
        return Object.isNone(this._delegate) === false;
    },

    bind: function(delegate) {
        if (this.isBound()) {
            throw new Error('frame component is already bound');
        }

        this._delegate = delegate;
        this._overlay.bind(delegate);
        return this;
    },

    unbind: function() {
        if (this.isBound() === false) {
            throw new Error('frame component is not bound');
        }

        this._overlay.unbind(this._delegate);
        this._delegate = undefined;
        return this;
    },

    backend: function(backend) {
        return Object.property(this, '_backend', backend);
    },

    delegate: function() {
        return this._delegate;
    },

    autoActivate: function(auto) {
        return Object.property(this, '_autoActivate', auto);
    },

    overlay: function() {
        return this._overlay;
    },

    overlayDelay: function(delay) {
        return Object.property(this, '_overlayDelay', delay);
    },

    preferredSize: function() {
        return this._delegate ? creme.layout.preferredSize(this._delegate, 2) : {width: 0, height: 0};
    }
});
}(jQuery));
