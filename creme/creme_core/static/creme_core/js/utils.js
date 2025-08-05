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

creme.utils = creme.utils || {};

creme.utils.openWindow = function (url, name, params) {
    window[name] = window.open(url, name, params || 'menubar=no, status=no, scrollbars=yes, menubar=no, width=800, height=600');
};

creme.utils.reload = function () {
    // reload without adding lines to history
    window.location.replace(window.location.href);
};

creme.utils.redirect = function(url) {
    window.location.assign(url);
};

creme.utils.locationRelativeUrl = function() {
    // remove 'http://host.com'
    return _.toRelativeURL(window.location.href).fullPath();
};

creme.utils.goTo = function(url, data) {
    if (Object.isEmpty(data)) {
        creme.utils.redirect(url);
    } else {
        var urlinfo = _.toRelativeURL(url);

        if (Object.isString(data)) {
            data = _.decodeURLSearchData(data);
        }

        urlinfo.searchData($.extend({}, urlinfo.searchData(), data));
        creme.utils.redirect(urlinfo.href());
    }
};

/*
creme.utils.showPageLoadOverlay = function() {
    console.warn('creme.utils.showPageLoadOverlay is deprecated; Use creme.dialog.Overlay instead.');
    creme.utils.loading('', false);
};
*/

/*
creme.utils.hidePageLoadOverlay = function() {
    console.warn('creme.utils.showPageLoadOverlay is deprecated; Use creme.dialog.Overlay instead.');
    creme.utils.loading('', true);
};
*/

/*
creme.utils.loading = function(div_id, is_loaded, params) {
    console.warn('creme.utils.loading is deprecated; Use creme.dialog.Overlay instead.');

    var overlay = creme.utils._overlay;

    if (overlay === undefined) {
        overlay = creme.utils._overlay = new creme.dialog.Overlay();
        overlay.bind($('body'))
               .addClass('page-loading')
               .content($('<h2>').append($('<img>').attr('src', creme_media_url("images/wait.gif")),
                                         $('<span>').text(gettext('Loading…'))));

        overlay._loadstack = 0;
    }

    overlay._loadstack += !is_loaded ? 1 : -1;

    var visible = overlay._loadstack > 0;
    overlay.update(visible, null, visible ? 100 : 0);
};
*/

/*
creme.utils.confirmSubmit = function(atag, msg) {
    console.warn('creme.utils.confimSubmit is now deprecated; should use actions instead');
    creme.dialogs.confirm(msg || gettext('Are you sure?'))
                 .onOk(function() {
                      $('form', $(atag)).trigger('submit');
                  })
                 .open();
};
*/

creme.utils.scrollTo = function(element) {
    if (Object.isNone(element) === false) {
        var outer_height = $('.header-menu').outerHeight();
        var position = $.extend({left: 0, top: 0}, $(element).position());

        window.scrollTo(position.left, position.top - outer_height);
    }
};

creme.utils.scrollBack = function(position, speed) {
    // Safari => document.body
    // Other => document.documentElement
    if (Object.isNone(position)) {
        return document.body.scrollTop || document.documentElement.scrollTop;
    }

    speed = speed || 0;

    if (speed !== 0) {
        $(document.body).animate({scrollTop: position}, speed);
        $(document.documentElement).animate({scrollTop: position}, speed);
    } else {
        document.body.scrollTop = position;
        document.documentElement.scrollTop = position;
    }
};

creme.utils.showErrorNReload = function(delay) {
    delay = Object.isNone(delay) ? 3000 : delay;
    var dialog = creme.dialogs.warning('<p><b>' + gettext("Error!") + '</b></p><p>' + gettext("The page will be reloaded!") + '</p>')
                              .onClose(function() {
                                  clearTimeout(timeout);
                                  creme.utils.reload();
                              });

    var timeout = setTimeout(function() {
        dialog.close();
    });

    dialog.open();
};

creme.utils.ajaxQuery = function(url, options, data) {
    /*
     * Build action that executes an AJAX query with some side effects.
     *
     * @param {String} url
     *     URL of the ajax query
     *
     * @param {Object} data
     *     Data sent to the ajax query. Can be either post data or url parameters.
     *
     * @param {String|Boolean} options.confirm
     *     If true, shows default confirmation message "Are you sure?"
     *     If a string, shows the given confirmation message
     *
     * @param {Boolean} options.reloadOnFail
     *     If true, reload the entire page on failure
     * @param {Boolean} options.warnOnFail
     *     If true, Shows warning message on failure.
     * @param {String} options.warnOnFailTitle
     *     Warning message shown when options.warnOnFail is true.
     *
     * @param {Boolean} options.reloadOnSuccess
     *     If true, reload the entire page on success.
     * @param {String} options.messageOnSuccess
     *     Display the given message on success.
     */
    options = $.extend({
        action: 'get',
        warnOnFail: true
    }, options || {});

    var action = new creme.component.Action(function() {
        var self = this;
        var query = creme.ajax.query(url, options, data);

        var _fail = function(data, error) {
            self.fail(data, error);

            if (options.reloadOnFail) {
                creme.utils.reload();
            }
        };

        var _success = function(result) {
            self.done(result);

            if (options.reloadOnSuccess) {
                creme.utils.reload();
            }
        };

        query.onFail(function(event, data, error) {
                  if (options.warnOnFail) {
                      var message = Object.isString(data) ? data : (error.message || gettext("Error"));
                      creme.dialogs.error(message, {title: options.warnOnFailTitle}, error)
                                   .onClose(function() {
                                        _fail(data, error);
                                    })
                                   .open();
                  } else {
                      _fail(data, error);
                  }
              })
             .onDone(function(event, result) {
                  if (options.messageOnSuccess) {
                      creme.dialogs.html('<p>%s</p>'.format(options.messageOnSuccess))
                                   .onClose(function() {
                                        _success(result);
                                    })
                                   .open();
                  } else {
                      _success(result);
                  }
              });

/*
        if (options.waitingOverlay) {
            console.warn('The option "waitingOverlay" of creme.utils.ajaxQuery is deprecated.');

            query.onStart(function() {
                      creme.utils.showPageLoadOverlay();
                  })
                 .onComplete(function() {
                      creme.utils.hidePageLoadOverlay();
                  });
        }
*/

        if (options.confirm) {
            var confirmMessage = Object.isString(options.confirm) ? options.confirm : gettext("Are you sure?");

            creme.dialogs.confirm('<h4>%s</h4>'.format(confirmMessage))
                         .onOk(function() { query.start(); })
                         .onClose(function() { self.cancel(); })
                         .open({width: 250, height: 150});
        } else {
            query.start();
        }
    }, options);

    return action;
};

creme.utils.isHTMLDataType = function(dataType) {
    return Object.isString(dataType) &&
           ['html', 'text/html'].indexOf(dataType.toLowerCase()) !== -1;
};

// Temporary HACK : Fix used in some <a onclick="..."> tags to prevent multiple clicks.
creme.utils.clickOnce = function(element, func) {
    element = $(element);

    if (element.is(':not(.clickonce') && Object.isFunc(func)) {
        element.addClass('clickonce');
        return func.apply(this, Array.from(arguments).slice(2));
    } else {
        return false;
    }
};

creme.utils.jQueryToMomentDateFormat = function(format) {
    /*
     * Converts a format string for ui.datepicker into a MomentJS one.
     * https://momentjs.com/docs/#/parsing/string-format/
     * https://api.jqueryui.com/datepicker/
     */
    return format.replace(/y+/g, function(match) {
        return match.length > 1 ? 'YYYY' : 'YY';
    }).replace(/d+/g, function(match) {
        return match.length > 1 ? 'DD' : 'D';
    }).replace(/m+/g, function(match) {
        return match.length > 1 ? 'MM' : 'M';
    });
};

}(jQuery));
