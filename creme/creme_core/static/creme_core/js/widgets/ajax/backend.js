/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2021  Hybird

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
jQuery.ajaxSettings.traditional = true;

creme.ajax = creme.ajax || {};

creme.ajax.Backend = function(options) {
    this.options = $.extend({
        dataType: 'html',
        sync: false,
        debug: false
    }, options || {});
};

creme.ajax.Backend.prototype = {
    get: function(url, data, on_success, on_error, options) {
        var opts = $.extend(true, {method: 'GET'}, this.options, options);

        if (opts.debug) {
            console.log('creme.ajax.Backend > GET', url, ' > data:', data, ', options:', opts);
        }

        creme.ajax.jqueryAjaxSend(url, data, on_success, on_error, opts);
    },

    post: function(url, data, on_success, on_error, options) {
        var opts = $.extend(true, {method: 'POST'}, this.options, options);

        if (opts.debug) {
            console.log('creme.ajax.Backend > POST', url, ' > data:', data, ', options:', opts);
        }

        creme.ajax.jqueryAjaxSend(url, data, on_success, on_error, opts);
    },

    submit: function(form, on_success, on_error, options) {
        var opts = $.extend(true, {}, this.options, options);

        if (opts.debug) {
            console.log('creme.ajax.Backend > SUBMIT', form.attr('action'), '> options:', opts);
        }

        creme.ajax.jqueryFormSubmit(form, on_success, on_error, opts);
    },

    query: function(options) {
        return new creme.ajax.Query(options, this);
    }
};

creme.ajax.LOCALIZED_ERROR_MESSAGES = {
    '0':   gettext('Connection Refused'),
    '400': gettext('Bad Request'),
    '401': gettext('Unauthorized'),
    '403': gettext('Forbidden Access'),
    '404': gettext('Not Found'),
    '406': gettext('Not Acceptable'),
    '409': gettext('Conflict'),
    '500': gettext('Internal Error')
};

creme.ajax.localizedErrorMessage = function(xhr) {
    var status = Object.isEmpty(xhr) ? '200' : (['number', 'string'].indexOf(typeof xhr) !== -1 ? xhr : (xhr.status || '200'));
    var message = creme.ajax.LOCALIZED_ERROR_MESSAGES[status];

    return message || (gettext('Error') + (status && status !== '200' ? ' (' + status + ')' : ''));
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

creme.ajax.jqueryFormSubmit = function(form, successCb, errorCb, options) {
    options = options || {};

    var formUrl = form.attr('action');

    form.attr('action', options.action || formUrl);

    function _parseIFrameResponseStatus(responseText) {
        if (/^HTTPError [0-9]+$/.test(responseText)) {
            return parseInt(responseText.substr('HTTPError '.length));
        } else {
            return 200;
        }
    }

    function _onSuccess(responseText, statusText, xhr, form) {
        form.attr('action', formUrl);

        if (submitOptions.iframe && xhr.status === 0) {
            xhr.status = _parseIFrameResponseStatus(responseText);
        }

        if (xhr.status === 200) {
            if (Object.isFunc(successCb)) {
                successCb(responseText, statusText, xhr, form);
            }
        } else if (Object.isFunc(errorCb)) {
            errorCb(responseText, {
                type:    "request",
                status:  xhr.status,
                message: "HTTP - " + xhr.status + " error",
                request: xhr
            });
        }
    };

    function _onError(xhr) {
        if (Object.isFunc(errorCb)) {
            errorCb(xhr.responseText, {
                type:   "request",
                status:  xhr.status,
                message: "HTTP - " + xhr.status + " error",
                request: xhr});
        }
    };

    // disable iframe if no file input in form
    var useIFrame = $('input[type=file]', form).length > 0;
    var headers = {};

    if ($('input[name="csrfmiddlewaretoken"]', form).length === 0) {
        headers = {'X-CSRFToken': creme.ajax.cookieCSRF()};
    }

    var submitOptions = $.extend(true, {
        iframe: useIFrame,
        success: _onSuccess,
        error: _onError,
        headers: headers
    }, options);

    $(form).ajaxSubmit(submitOptions);
};

// TODO : replace success_cb/error_cb by listeners.
creme.ajax.jqueryAjaxSend = function(url, data, successCb, errorCb, options) {
    options = options || {};

    function _onSuccess(data, textStatus, xhr) {
        if (Object.isFunc(successCb)) {
            successCb(data, textStatus, xhr);
        }
    };

    function _errorMessage(xhr, textStatus) {
        if (textStatus === 'parseerror') {
            return "JSON parse error";
        } else {
            return "HTTP ${status} - ${statusText}".template(xhr);
        }
    };

    function _onError(xhr, textStatus, errorThrown) {
        if (Object.isFunc(errorCb)) {
            errorCb(xhr.responseText, {
                type: "request",
                status: xhr.status,
                request: xhr,
                message: _errorMessage(xhr, textStatus)
            });
        }
    };

    var csrf = creme.ajax.cookieCSRF();
    var headers = {};

    if (Object.isEmpty(csrf) === false) {
        headers = {'X-CSRFToken': csrf};
    }

    var ajaxOptions = $.extend(true, {
        async:    !options.sync,
        type:     options.method || 'GET',
        url:      url,
        data:     data || {},
        dataType: options.dataType || 'json',
        headers:  headers,
        success:  _onSuccess,
        error:    _onError
    }, options);

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
