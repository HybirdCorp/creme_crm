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

/*
 * Requires : jQuery
 *            creme.utils.js
 */

(function($) {
"use strict";

creme.ajax = creme.ajax || {};

/* istanbul ignore next */
creme.ajax.submit = function(form, data, options) {
    console.error('creme.ajax.submit should not be used; Use creme.ajax.jqueryFormSubmit or creme.ajax.Backend().submit instead');
    // Tip: If data === true => data are taken from the form
    var $form = $(form);

    var defaults = {
        method: $form.attr('method'),
        action: ($form.attr('action') === "") ? window.location.href : $form.attr('action'),
        async: true,
        cache: true,
        beforeSend: null,
        success: null,
        beforeError: null,
        beforeComplete: null,
        error: function() {
            creme.utils.showErrorNReload();
        },
        afterError: null,
        complete: null
    };

    var opts = $.extend(defaults, options);
    if (data === true) {
        data = $form.serialize();
    }

    $.ajax({
          url: opts.action,
          type: opts.method,
          data: data,
          async: opts.async,
          beforeSend: function(request) {
              creme.utils.loading('loading', false, {});
              if (opts.beforeSend) opts.beforeSend(request);
          },
          success: function(returnedData, status) {
            if (opts.success) opts.success(returnedData, status);
          },
          error: function(request, status, error) {
              if (opts.beforeError) opts.beforeError(request, status, error);
              if (opts.error) opts.error(request, status, error);
              if (opts.afterError) opts.afterError(request, status, error);
          },
          complete: function(request, status) {
              if (opts.beforeComplete) opts.beforeComplete(request, status);
              creme.utils.loading('loading', true, {});
              if (opts.complete) opts.complete(request, status);
          }
    });
};

/* istanbul ignore next */
creme.ajax.ajax = function(options) {
    console.warn('creme.ajax.ajax is deprecated. Use creme.ajax.Query(...) instead');
    options = $.extend({
        type: "GET",
        url: "",
        async: true,
        data: {},
        dataType: "html",
        cache: true,
        beforeSend: null,
        success: null,
        beforeError: null,
        beforeComplete: null,
        error: function() {
            creme.utils.showErrorNReload();
        },
        afterError: null,
        complete: null
    }, options);

    $.ajax({
          url: options.url,
          type: options.type,
          data: options.data,
          async: options.async,
          dataType: options.dataType,
          beforeSend: function(request) {
              creme.utils.loading('loading', false, {});
              if (options.beforeSend && $.isFunction(options.beforeSend)) options.beforeSend(request);
          },
          success: function(returnedData, status) {
            if (options.success && $.isFunction(options.success)) options.success(returnedData, status);
          },
          error: function(request, status, error) {
              if (options.beforeError && $.isFunction(options.beforeError)) options.beforeError(request, status, error);
              if (options.error && $.isFunction(options.error)) options.error(request, status, error);
              if (options.afterError && $.isFunction(options.afterError)) options.afterError(request, status, error);
          },
          complete: function (request, status) {
              if (options.beforeComplete) options.beforeComplete(request, status);
              creme.utils.loading('loading', true, {});
              if (options.complete) options.complete(request, status);
          }
    });
};

/* istanbul ignore next */
creme.ajax.get = function(options) {
    console.warn('creme.ajax.get is deprecated. Use creme.ajax.Query(...).get(...) instead');
    creme.ajax.ajax($.extend({type: "GET"}, options));
};

/* istanbul ignore next */
creme.ajax.post = function(options) {
    console.warn('creme.ajax.get is deprecated. Use creme.ajax.Query(...).post(...) instead');
    creme.ajax.ajax($.extend({type: "POST"}, options));
};

/* istanbul ignore next */
creme.ajax.reloadContent = function($target, target_url) {
    console.warn('creme.ajax.reladContent is deprecated. Use creme.ajax.Query(...).onDone(...) instead');
    creme.ajax.get({
        url: target_url,
        success: function(data) {
            $target.empty().html(data);
        }
    });
};

creme.ajax.json = {};
/*
creme.ajax.json._handleSendError = function(req, textStatus, errorThrown) {
    var message;

    switch (textStatus) {
        case "parsererror":
            message = "JSON parse error"; break;
        default:
            message = String(req.status) + " " + req.statusText;
    };

    return {
        type: "request",
        status: req.status,
        request: req,
        message: message
    };
};
*/

creme.ajax.json.send = function(url, data, success_cb, error_cb, sync, method, parameters) {
    console.warn('creme.ajax.json.send is deprecated. Use creme.ajax.Query(...) instead');

    creme.ajax.jqueryAjaxSend(url, data, success_cb, error_cb, $.extend({
        sync: sync,
        method: method
    }, parameters || {}));
/*
    var ajax_parameters = {
        async: !sync,
        type: method,
        url: url,
        data: data !== undefined ? data : '',
        dataType: "json",
        success: function(data, textStatus) {
            if (Object.isFunc(success_cb)) {
                success_cb(data, textStatus);
            }
        },
        error: function(req, textStatus, errorThrown) {
            if (Object.isFunc(error_cb)) {
                error_cb(req.responseText, creme.ajax.json._handleSendError(req, textStatus, errorThrown));
            }
        }
    };

    if (parameters !== undefined) {
        ajax_parameters = $.extend(ajax_parameters, parameters);
    }

    $.ajax(ajax_parameters);
*/
};

creme.ajax.json.post = function(url, data, success_cb, error_cb, sync, parameters) {
    creme.ajax.json.send(url, data, success_cb, error_cb, sync, "POST", parameters);
};

creme.ajax.json.get = function(url, data, success_cb, error_cb, sync, parameters) {
    creme.ajax.json.send(url, data, success_cb, error_cb, sync, "GET", parameters);
};

// Make sure the incoming data is actual JSON
// Logic borrowed from http://json.org/json2.js
// TODO : Factorise with creme.utils.JSON
/* istanbul ignore next */
creme.ajax.json.isvalid = function(data) {
    console.warn('creme.ajax.json.parse is deprecated. Use creme.utils.JSON.isValid');
    return Object.isString(data) &&
           /^[\],:{}\s]*$/.test(data.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
                                    .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
                                    .replace(/(?:^|:|,)(?:\s*\[)+/g, ""));
};

// Code copied from JQuery 1.4.*
// TODO : Factorise with creme.utils.JSON
/* istanbul ignore next */
creme.ajax.json.parse = function(data) {
    console.warn('creme.ajax.json.parse is deprecated. Use JSON.parse and catch exceptions instead');
    if (!data || !Object.isString(data)) {
        return null;
    }

    data = data.trim();

    if (creme.ajax.json.isvalid(data)) {
        try {
            // Try to use the native JSON parser first
            if (window.JSON && window.JSON.parse) {
                return window.JSON.parse(data);
            } else {
                return $.parseJSON(data);
            }
        } catch (err) {
            // console.log( "Invalid JSON: " + data );
            return null;
        }
    } else {
        // console.log( "Invalid JSON: " + data );
        return null;
     }
 };

/* Never used. Anyway creme.ajax.jqueryFormSubmit() should be used instead
creme.ajax.json.ajaxFormSubmit = function($form, success_cb, error_cb, sync, parameters) {
    creme.ajax.json.post($form.attr('action'),
                         $form.serialize(),
                         success_cb || function(data) { $form.html(data.form); },
                         error_cb, sync, parameters
    );
};
*/

}(jQuery));
