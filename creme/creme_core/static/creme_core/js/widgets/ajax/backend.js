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

(function($) {
"use strict";

$(document).ajaxSend(function(event, xhr, settings) {
    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader("X-CSRFToken", creme.ajax.cookieCSRF());
    }
});

// Traditional parameter serialization (true: a=1&a=2&b=3, false: a[]=1&a[]=2&b=3)
// So, with false if a param is used more than once "[]" is appended to the param name
// This setting is deprecated since jQuery 1.9 see (https://bugs.jquery.com/ticket/12137)
// jQuery.ajaxSettings.traditional = true;

creme.ajax = creme.ajax || {};

creme.ajax.Backend = function(options) {
    this.options = $.extend({
        dataType: 'html',
        sync: false,
        debug: false,
        // Keep using traditional=true as default to replace ajaxSettings.traditional
        traditional: true
    }, options || {});
};

creme.ajax.Backend.prototype = {
    get: function(url, data, successCb, errorCb, options) {
        var opts = $.extend(true, {}, this.options, options);
        var debug = _.pop(opts, 'debug', false);

        if (debug) {
            console.log('creme.ajax.Backend > GET', url, ' > data:', data, ', options:', opts);
        }

        return creme.ajax.jqueryAjaxSend(Object.assign({
            url: url,
            method: 'GET',
            body: data
        }, opts), {
            done: successCb,
            fail: errorCb
        });
    },

    post: function(url, data, successCb, errorCb, options) {
        var opts = $.extend(true, {}, this.options, options);
        var debug = _.pop(opts, 'debug', false);

        if (debug) {
            console.log('creme.ajax.Backend > POST', url, ' > data:', data, ', options:', opts);
        }

        return creme.ajax.jqueryAjaxSend(Object.assign({
            url: url,
            method: 'POST',
            body: data,
            csrf: creme.ajax.cookieCSRF()
        }, opts), {
            done: successCb,
            fail: errorCb
        });
    },

    submit: function(form, successCb, errorCb, options) {
        var opts = $.extend(true, {}, this.options, options);
        var formEl = form.get(0);
        var debug = _.pop(opts, 'debug', false);

        if (debug) {
            console.log('creme.ajax.Backend > SUBMIT', form.attr('action'), '> options:', opts);
        }

        var url = _.pop(opts, 'url', _.pop(opts, 'action', form.attr('action'))) || '';
        var data = new FormData(formEl);
        var extraData = _.pop(opts, 'data', opts.extraData || {});
        var csrf = data.get('csrfmiddlewaretoken') || creme.ajax.cookieCSRF();

        return creme.ajax.jqueryAjaxSend(Object.assign({
            url: url,
            method: 'POST',
            body: data,
            extraData: extraData,
            csrf: csrf
        }, opts), {
            done: successCb,
            fail: errorCb
        });
    },

    query: function(options) {
        return new creme.ajax.Query(options, this);
    }
};

creme.ajax.LOCALIZED_ERROR_MESSAGES = {
    0:   gettext('Connection Refused'),
    400: gettext('Bad Request'),
    401: gettext('Unauthorized'),
    403: gettext('Forbidden Access'),
    404: gettext('Not Found'),
    406: gettext('Not Acceptable'),
    409: gettext('Conflict'),
    500: gettext('Internal Error')
};

creme.ajax.localizedErrorMessage = function(status) {
    status = isNaN(status) ? parseInt(_.isString(status) ? status : (status || {}).status) : status;
    var message = status >= 0 ? creme.ajax.LOCALIZED_ERROR_MESSAGES[status] : gettext('Error');

    return message || (gettext('Error') + (status > 0 ? ' (' + status + ')' : ''));
};

// mock XHR object (thanks to jquery.form author)
creme.ajax.XHR = function(options) {
    $.extend(this, {
        aborted:      0,
        responseText: '',
        responseXML:  null,
        status:       200,
        statusText:   'n/a',

        getAllResponseHeaders: function() {},
        getResponseHeader: function() {},
        setRequestHeader: function() {},
        abort: function(status) {}
    }, options || {});
};

creme.ajax.AjaxResponse = function(status, data, xhr) {
    this.type = "request";
    this.status =  status;
    this.message = data;
    this.request = xhr || new creme.ajax.XHR({responseText: data, status: status});
};

// Code from https://docs.djangoproject.com/en/1.7/ref/contrib/csrf/#ajax
creme.ajax.cookieAttr = function(name) {
    if (Object.isEmpty(name) || Object.isEmpty(document.cookie)) {
        return null;
    }

    var cookies = document.cookie.split(';');

    for (var i = 0; i < cookies.length; i++) {
        var item = cookies[i].trim().split('=');

        if (item.length > 1 && item[0] === name) {
            return decodeURIComponent(item[1]);
        }
    }

    return null;
};

creme.ajax.cookieCSRF = function() {
    return creme.ajax.cookieAttr('csrftoken');
};

creme.ajax.serializeFormAsDict = function(form, extraData) {
    extraData = extraData || {};
    var data = {};
    var addEntry = function(data, key, value) {
        if (!Object.isEmpty(key) && !Object.isNone(value)) {
            if (data[key] === undefined) {
                data[key] = Array.isArray(value) ? value : [value];
            } else if (Array.isArray(value)) {
                data[key].extend(value);
            } else {
                data[key].push(value);
            }
        }
    };

    $(form).serializeArray().forEach(function(e) {
        addEntry(data, e.name, e.value);
    });

    for (var key in extraData) {
        addEntry(data, key, extraData[key]);
    }

    return data;
};

function xhrEventLoadedPercent(event) {
    var position = event.loaded || event.position; /* event.position is deprecated */
    var total = event.total;
    return (event.lengthComputable > 0 || event.lengthComputable === true) ? Math.ceil(position / total * 100) : 0;
}

/*
 * Workaround because jqXHR does not expose upload property
 * https://github.com/jquery-form/form/blob/master/src/jquery.form.js#L401-L422
 */
function progressXHR(listeners) {
    listeners = listeners || {};

    var xhr = $.ajaxSettings.xhr();

    if (listeners.uploadProgress && xhr.upload) {
        xhr.upload.addEventListener('progress', function(event) {
            event.loadedPercent = xhrEventLoadedPercent(event);
            listeners.uploadProgress(event);
        }, false);
    }

    if (listeners.progress) {
        xhr.addEventListener('progress', function(event) {
            event.loadedPercent = xhrEventLoadedPercent(event);
            listeners.progress(event);
        }, false);
    }

    return xhr;
}

function xhrErrorMessage(xhr, textStatus, errorThrown) {
    if (textStatus === 'parseerror') {
        return "JSON parse error";
    } else {
        return "HTTP ${status} - ${statusText}".template({
            status: xhr.status || 0,
            statusText: xhr.statusText || errorThrown || gettext('Error')
        });
    }
};


// TODO : Replace listeners by a Promise with 'uploadProgress' & 'progress' callbacks
creme.ajax.jqueryAjaxSend = function(options, listeners) {
    options = options || {};
    listeners = Object.assign({
        done: _.pop(options, 'success'),   /* keeps compatibility with the old API */
        fail: _.pop(options, 'error'),
        progress: _.pop(options, 'progress'),
        uploadProgress: _.pop(options, 'uploadProgress')
    }, listeners || {});

    var csrf = options.csrf === true ? creme.ajax.cookieCSRF() : options.csrf;
    var headers = Object.assign({}, options.headers || {}, Object.isEmpty(csrf) ? {} : {'X-CSRFToken': csrf});
    var method = (options.method || options.type || 'GET').toUpperCase();
    var body = (options.data || options.body);
    var extraData = _.pop(options, 'extraData', {});

    function _onSuccess(data, textStatus, xhr) {
        if (Object.isFunc(listeners.done)) {
            listeners.done(data, textStatus, xhr);
        }
    };

    function _onError(xhr, textStatus, errorThrown) {
        if (Object.isFunc(listeners.fail)) {
            listeners.fail(xhr.responseText, {
                type: "request",
                status: xhr.status,
                request: xhr,
                message: xhrErrorMessage(xhr, textStatus, errorThrown)
            });
        }
    };

    var ajaxOptions = $.extend(true, {
        async:    !_.pop(options, 'sync'),
        type:     method,
        url:      options.url,
        data:     body,
        dataType: options.dataType || 'json',
        headers:  headers,
        success:  _onSuccess,
        error:    _onError
    }, options);

    // uploadProgress callback needs a custom XHR instance to read the event.
    if (listeners.uploadProgress || listeners.progress) {
        ajaxOptions.xhr = function() {
            return progressXHR(listeners);
        };
    }

    // When body is FormData we have to disable all post processing from jquery
    if (body instanceof FormData) {
        ajaxOptions.processData = false;
        ajaxOptions.contentType = false;

        _.assignFormData(body, extraData);
    } else if (!Object.isEmpty(extraData)) {
        ajaxOptions.data = Object.assign(body || {}, extraData);
    }

    return $.ajax(ajaxOptions);
};

var __defaultBackend = new creme.ajax.Backend();

creme.ajax.defaultBackend = function(backend) {
    if (backend === undefined) {
        return __defaultBackend;
    }

    if (creme.ajax.Backend.prototype.isPrototypeOf(backend) === false) {
        throw new Error('Default ajax backend must be a creme.ajax.Backend instance');
    }

    __defaultBackend = backend;
};

}(jQuery));
