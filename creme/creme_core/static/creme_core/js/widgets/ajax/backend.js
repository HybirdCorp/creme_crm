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

creme.ajax.Backend = function(options) {
    this.options = $.extend({
        dataType:'html',
        sync:false,
        debug:false
    }, options || {});
}

creme.ajax.Backend.prototype = {
    get:function(url, data, on_success, on_error, options)
    {
        var opts = $.extend({}, this.options, options);

        if (opts.debug)
            console.log('creme.ajax.Backend > GET', url, ' > data:', data, ', options:', opts);

        creme.ajax.json.send(url, data, on_success, on_error, opts.sync, "GET", opts);
    },

    post:function(url, data, on_success, on_error, options)
    {
        var opts = $.extend({}, this.options, options);

        if (opts.debug)
            console.log('creme.ajax.Backend > POST', url, ' > data:', data, ', options:', opts);

        creme.ajax.json.send(url, data, on_success, on_error, opts.sync, "POST", opts);
    },

    submit:function(form, on_success, on_error, options)
    {
        var opts = $.extend({}, this.options, options);

        if (opts.debug)
            console.log('creme.ajax.Backend > SUBMIT', form.attr('action'), '> options:', opts);

        creme.ajax.jqueryFormSubmit(form, on_success, on_error, opts);
    }
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
}

creme.ajax.AjaxResponse = function(status, data, xhr) {
    return {
        type:    "request",
        status:  status,
        message: data,
        request: xhr || new creme.ajax.XHR({responseText: data, status: status})
    };
};
