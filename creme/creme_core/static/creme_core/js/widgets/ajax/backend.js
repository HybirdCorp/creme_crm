/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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
        var opts = $.extend({method: 'GET'}, this.options, options);

        if (opts.debug) {
            console.log('creme.ajax.Backend > GET', url, ' > data:', data, ', options:', opts);
        }

        creme.ajax.jqueryAjaxSend(url, data, on_success, on_error, opts);
    },

    post: function(url, data, on_success, on_error, options) {
        var opts = $.extend({method: 'POST'}, this.options, options, true);

        if (opts.debug) {
            console.log('creme.ajax.Backend > POST', url, ' > data:', data, ', options:', opts);
        }

        creme.ajax.jqueryAjaxSend(url, data, on_success, on_error, opts);
    },

    submit: function(form, on_success, on_error, options) {
        var opts = $.extend({}, this.options, options, true);

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
    return $.extend({
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
    return {
        type:    "request",
        status:  status,
        message: data,
        request: xhr || new creme.ajax.XHR({responseText: data, status: status})
    };
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

creme.ajax.jqueryFormSubmit = function(form, success_cb, error_cb, options) {
    options = options || {};

    var form_action = form.attr('action');
    var needs_iframe = $('input[type=file]', form).length > 0; // disable iframe if no file input in form

    form.attr('action', options.action || form_action);

    function parse_iframe_response_status(responseText) {
        if (/^HTTPError [0-9]+$/.test(responseText)) {
            return parseInt(responseText.substr('HTTPError '.length));
        } else {
            return 200;
        }
    }

    var submit_options = {
        iframe: needs_iframe,
        success: function(responseText, statusText, xhr, form) {
            form.attr('action', form_action);

            if (needs_iframe && xhr.status === 0) {
                xhr.status = parse_iframe_response_status(responseText);
            }

            if (xhr.status === 200) {
                if (success_cb !== undefined) {
                    success_cb(responseText, statusText, xhr, form);
                }

                return;
            }

            if (error_cb !== undefined) {
                error_cb(responseText, {
                    type:    "request",
                    status:  xhr.status,
                    message: "HTTP - " + xhr.status + " error",
                    request: xhr
                });
            }
        },
        error: function(xhr) {
            if (error_cb !== undefined) {
                error_cb(xhr.responseText, {
                    type:   "request",
                    status:  xhr.status,
                    message: "HTTP - " + xhr.status + " error",
                    request: xhr});
            }
        }
    };

    submit_options = $.extend({}, submit_options, options, true);

    if ($('input[name="csrfmiddlewaretoken"]', form).length === 0) {
        submit_options.headers = $.extend(options.headers || {}, {'X-CSRFToken': creme.ajax.cookieCSRF()});
    }

    $(form).ajaxSubmit(submit_options);
};

// TODO : This code is duplicated from creme.ajax.json.send and will replace it in the future
// TODO : replace success_cb/error_cb by listeners.
creme.ajax.jqueryAjaxSend = function(url, data, success_cb, error_cb, options) {
    options = options || {};

    var csrf = creme.ajax.cookieCSRF();

    var ajax_options = $.extend({
        async:    !options.sync,
        type:     options.method || 'GET',
        url:      url,
        data:     data !== undefined ? data : '',
        dataType: "json",
        success: function(data, textStatus, xhr) {
            if (Object.isFunc(success_cb)) {
                success_cb(data, textStatus, xhr);
            }
        },
        error: function(req, textStatus, errorThrown) {
            if (Object.isFunc(error_cb)) {
                error_cb(req.responseText, creme.ajax.json._handleSendError(req, textStatus, errorThrown));
            }
        }
    }, options);

    if (Object.isEmpty(csrf) === false) {
        ajax_options.headers = $.extend(options.headers || {}, {'X-CSRFToken': csrf});
    }

    $.ajax(ajax_options);
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
