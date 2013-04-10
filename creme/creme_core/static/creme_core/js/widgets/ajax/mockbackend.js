/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2011  Hybird

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

creme.ajax.MockAjaxBackend = function(options) {
    $.extend(this.options, {
        delay: 500
    }, options || {});

    this.GET =  {};
    this.POST = {};
}

creme.ajax.MockAjaxBackend.prototype = new creme.ajax.Backend();
creme.ajax.MockAjaxBackend.prototype.constructor = creme.ajax.Backend;

$.extend(creme.ajax.MockAjaxBackend.prototype, {
    send: function(url, data, method, on_success, on_error, options)
    {
        var self = this;
        var options = $.extend({}, this.options, options);

        if (options.sync !== true)
        {
             options.sync = true;
             var delay = options.delay !== undefined ? options.delay : 500;

             window.setTimeout(function() {self.send(url, data, method, on_success, on_error, options);}, delay);
             return;
        }

        var response = method !== undefined ? method[url] : undefined;

        if (response === undefined)
            response = this.response(404, '');

        if (typeof response === 'function') {
            response = creme.object.invoke(response, url, data, options);
        }

        if (options.debug)
            console.log('mockajax > send > url:', url, 'options:', options, 'response:', response);

        if (response.status !== 200)
            return creme.object.invoke(on_error, response.responseText, new creme.ajax.AjaxResponse(response.status,
                                                                                                    response.responseText,
                                                                                                    response.xhr));

        return creme.object.invoke(on_success, response.responseText);
    },

    get:function(url, data, on_success, on_error, options) {
        return this.send(url, data, this.GET, on_success, on_error, options);
    },

    post:function(url, data, on_success, on_error, options) {
        return this.send(url, data, this.POST, on_success, on_error, options);
    },

    submit:function(form, on_success, on_error, options) {
        var options = options || {};
        var action = options.action || form.attr('action');
        return this.send(action, undefined, this.POST, on_success, on_error, options);
    },

    response: function(status, data) {
        return new creme.ajax.XHR({responseText: data, status: status});
    }
});
