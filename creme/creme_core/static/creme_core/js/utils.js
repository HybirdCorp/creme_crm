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

/* globals creme_media_url setTimeout clearTimeout */
(function($) {
"use strict";

creme.utils = creme.utils || {};

creme.utils.openWindow = function (url, name, params) {
    window[name] = window.open(url, name, params || 'menubar=no, status=no, scrollbars=yes, menubar=no, width=800, height=600');
};

creme.utils.reload = function (target) {
    target = target || window;
    creme.utils.goTo(target.location.href, target);
};

creme.utils.goTo = function(url, target) {
    target = target || window;
    target.location.href = url;
};

creme.utils.showPageLoadOverlay = function() {
    // console.log('show loading overlay');
    creme.utils.loading('', false);
};

creme.utils.hidePageLoadOverlay = function() {
    // console.log('hide loading overlay');
    creme.utils.loading('', true);
};

creme.utils.loading = function(div_id, is_loaded, params) {
    var overlay = creme.utils._overlay;

    if (overlay === undefined) {
        overlay = creme.utils._overlay = new creme.dialog.Overlay();
        overlay.bind($('body'))
               .addClass('page-loading')
               .content($('<h2>').append($('<img>').attr('src', creme_media_url("images/wait.gif")),
                                         $('<span>').text(gettext('Loading...'))));

        overlay._loadstack = 0;
    }

    overlay._loadstack += !is_loaded ? 1 : -1;

    var visible = overlay._loadstack > 0;
    overlay.update(visible, null, visible ? 100 : 0);
};

// TODO : deprecate it ? (only used by creme.utils.showInnerPopup)
creme.utils.showDialog = function(text, options, div_id) {
    var $div = $('#' + div_id);

    if ($div.size() === 0) {
        div_id = creme.utils.innerPopupUUID();
        $div = $('<div id="' + div_id + '"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    $div.html(text);

    __stackedPopups.push('#' + div_id);

    $div.dialog(jQuery.extend({
        buttons: [{text: gettext("Ok"),
                   click: function() {
                            $(this).dialog("close");
                   }
                 }
        ],
        closeOnEscape: false,
        title: '',
        modal: true,
        width: 'auto',
        close: function(event, ui) {
                $(this).dialog("destroy");
                $(this).remove();
        }
    }, options));
};


/*
creme.utils.confirmBeforeGo = function(url, ajax, ajax_options) { //todo: factorise (see ajaxDelete()) ??
    console.warn('creme.utils.confirmBeforeGo() is deprecated.');

    creme.dialogs.confirm(gettext("Are you sure ?"))
                 .onOk(function() {
                     if (ajax) {
                         $.ajax(jQuery.extend({
                                   url: url,
                                   data: {},
                                   success: function(data, status, req) {
                                       creme.utils.reload(); //todo: reload list-view content instead (so rename the function)
                                   },
                                   error: function(req, status, error) {
                                       creme.dialogs.warning(req.responseText || gettext("Error")).open();
                                   },
                                   complete: function(request, textStatus) {},
                                   sync: false,
                                   parameters : undefined
                               }, ajax_options)
                       );
                     } else {
                       creme.utils.goTo(url);
                     }
                  })
                 .open();
};
*/

creme.utils.confirmSubmit = function(atag, msg) {
    creme.dialogs.confirm(msg || gettext('Are you sure ?'))
                 .onOk(function() {
                      $('form', $(atag)).submit();
                  })
                 .open();
};

// Avoid the re-declaration in case of reload of creme_utils.js
var __stackedPopups = [];

creme.utils.innerPopupUUID = function() {
    var d = new Date();
    return d.getTime().toString() + Math.ceil(Math.random() * 1000000);
};

// BEWARE: DO NOT USE THIS, BECAUSE IT WILL PROBABLY BE REMOVED IN CREME 2.1
//    (we do not deprecate it because it is still used by list-view,
//     & we do not want to pollute terminal with annoying messages)
// NB: only used by creme.utils.innerPopupFormAction()
creme.utils.showInnerPopup = function(url, options, div_id, ajax_options, reload) {
    reload = reload || false;

    var $div = $('#' + div_id);
    if ($div.size() === 0) {
        div_id = creme.utils.innerPopupUUID();
        $div = $('<div id="' + div_id + '"  style="display:none;"></div>');
        $(document.body).append($div);
    }

    options = $.extend({
        reloadOnClose: false,
        buttons: [{
            text: gettext("Cancel"),
            click: function() {
                if ($.isFunction(options.cancel)) {
                    options.cancel($(this));
                }

                creme.utils.closeDialog($(this), reload);
            }
        }],
        close: function(event, ui) {
            creme.utils.closeDialog($(this), false);
        },
        open: function(event, ui) {
             var $me = $(event.target);
             var $form = $('[name=inner_body]', $me).find('form');
             var send_button = options.send_button; // function or boolean (if defined)

             // HACK : initialize widgets AFTER dialog opening.
             creme.widget.ready($me);

             if ($form.size() || send_button) {
                 var submit_handler;

                 if (Object.isFunc(send_button)) {
                     submit_handler = function(e) {
                         e.preventDefault();
                         e.stopPropagation();
                         send_button($me);
                     };
                 } else {
                     submit_handler = function(e) {
                         e.preventDefault();
                         e.stopPropagation();
                         creme.utils.handleDialogSubmit($me);
                     };
                 }

                 var buttons = $me.dialog('option', 'buttons');

                 // TODO: use the OS order for 'Cancel'/'OK' buttons
//                 buttons.unshift({
                 buttons.push({
                     text: options['send_button_label'] || gettext("Save"),
                     click: submit_handler
                 });

                 $me.dialog('option', 'buttons', buttons);
             }
        },
        closeOnEscape: false
    }, options || {});

    var query = creme.ajax.query(url, ajax_options);
    query.onDone(function(e, data) {
        creme.utils.showDialog(data, options, div_id);
    });

    query.onFail(function(e, data, error) {
        creme.dialogs.warning(data || gettext("Error during loading the page."))
                     .onClose(function() {
                         ajax_options.error(data, error);
                     })
                     .open();
    });

    query.get($.extend({whoami: div_id}, ajax_options.data));
    return div_id;
};

// TODO : This code is never reached in vanilla modules (new form dialog are used everywhere)
// Keep it for compatibility with client modules.
creme.utils.handleDialogSubmit = function(dialog) {
    console.warn('creme.utils.handleDialogSubmit() is deprecated.');

    var div_id = dialog.attr('id');
    var $form = $('[name=inner_body]', dialog).find('form');
    var post_url = $('[name=inner_header_from_url]', dialog).val();

    var data = $form.serialize();
    if (data.length > 0) data += "&";
    data += "whoami=" + div_id;

    $.ajax({
          type: $form.attr('method'),
          url: post_url,
          data: data,
          beforeSend: function(request) {
              creme.utils.loading('loading', false, {});
          },
          success: function(data, status) {
              var is_closing = data.startsWith('<div class="in-popup" closing="true"');

              if (!is_closing) {
                  data += '<input type="hidden" name="whoami" value="' + div_id + '"/>';

                  creme.widget.shutdown(dialog);
                  $('[name=inner_body]', '#' + div_id).html(data);
                  creme.widget.ready(dialog);

                  creme.utils.scrollTo($('.errorlist:first', '.non_field_errors'));
              } else {
                  var content = $(data);
                  var redirect_url = content.attr('redirect');
                  var force_reload = content.is('[force-reload]');
                  var delegate_reload = content.is('[delegate-reload]');

                  if (redirect_url) {
                      creme.utils.closeDialog(dialog, force_reload, undefined, redirect_url);
                  } else if (!delegate_reload) {
                      creme.utils.closeDialog(dialog, force_reload);
                  } else {
                      dialog.dialog('close');
                  }
              }
          },
          error: function(request, status, error) {
            creme.utils.showErrorNReload();
          },
          complete: function(XMLHttpRequest, textStatus) {
              creme.utils.loading('loading', true, {});
          }
    });

    return false;
};

creme.utils.scrollTo = function(element) {
    if (Object.isNone(element) === false) {
        var outer_height = $('.header-menu').outerHeight();
        var position = $.extend({left: 0, top: 0}, $(element).position());

        window.scrollTo(position.left, position.top + outer_height);
    }
};

creme.utils.closeDialog = function(dial, reload, beforeReloadCb, redirect_url) {
    $(dial).dialog("destroy");

    creme.widget.shutdown($(dial));
    $(dial).remove();

    // Remove dial from opened dialog array
    __stackedPopups.pop();

    if (Object.isFunc(beforeReloadCb)) {
        beforeReloadCb();
    }

    // Added by Jonathan 20/05/2010 in order to have a different callback url for inner popup if needs
    if (Object.isNotEmpty(redirect_url)) {
        creme.utils.goTo(redirect_url);
    } else if (reload === true) {
        // Get the dial's parent dialog or window
        creme.utils.reloadDialog(__stackedPopups[__stackedPopups.length - 1] || window);
    }
};

// BEWARE: DO NOT USE THIS, BECAUSE IT WILL PROBABLY BE REMOVED IN CREME 2.1
//    (we do not deprecate it because it is still used by list-view,
//     & we do not want to pollute terminal with annoying messages)
// NB: only used in creme.utils.closeDialog()
creme.utils.reloadDialog = function(dial) {
    if (dial === window) {
        creme.utils.reload();
        return;
    }

    var reload_url = $(dial).find('[name=inner_header_from_url]').val();
    var div_id     = $(dial).find('[name=whoami]').val();

    creme.ajax.query(reload_url)
              .onDone(function(event, data) {
                  $(dial).html(data);
              }).get({
                  whoami: div_id
              });
};

// TODO: deprecate ?
creme.utils.appendInUrl = function(url, strToAppend) {
    var index_get = url.indexOf('?');
    var get = "", anchor = "";

    if (index_get > -1) {
        get = url.substring(index_get, url.length);
        url = url.substring(0, index_get);
    }
    var index_anchor = url.indexOf('#');
    if (index_anchor > -1) {
        anchor = url.substring(index_anchor, url.length);
        url = url.substring(0, index_anchor);
    }

    if (strToAppend.indexOf('?') > -1) {
        url += strToAppend + get.replace('?', '&');
    } else if (strToAppend.indexOf('&') > -1) {
        url += get + strToAppend;
    } else url += strToAppend + get;

    return url + anchor;
};

/*
creme.utils.openQuickForms = function(element) {
    // NB: deprecated because it does not use reversed URLs
    //     creme.menu.openQuickForm() is OK, but need the new menu.
    console.warn('creme.utils.openQuickForms() is deprecated.');

    var uri = '/creme_core/quickforms/%s/%s';
    var type = $('[name="ct_id"]', element).val();
    var count = $('[name="entity_count"]', element).val();

    creme.dialogs.form(uri.format(type, count), {reloadOnSuccess: true}).open();
};
*/

creme.utils.showErrorNReload = function(delay) {
    delay = Object.isNone(delay) ? 3000 : delay;
    var dialog = creme.dialogs.warning('<p><b>' + gettext("Error !") + '</b></p><p>' + gettext("The page will be reload !") + '</p>')
                              .onClose(function() {
                                  clearTimeout(timeout);
                                  creme.utils.reload();
                              });

    var timeout = setTimeout(function() {
        dialog.close();
    });

    dialog.open();
};

creme.utils.confirmPOSTQuery = function(url, options, data) {
    options = $.extend({action: 'post'}, options || {});
    return creme.utils.confirmAjaxQuery(url, options, data);
};

creme.utils.confirmAjaxQuery = function(url, options, data) {
    options = $.extend({confirm: true}, options || {});
    return creme.utils.ajaxQuery(url, options, data);
};

creme.utils.ajaxQuery = function(url, options, data) {
    options = $.extend({
        action: 'get',
        warnOnFail: true
    }, options || {});

    var action = new creme.component.Action(function() {
        var self = this;
        var query = creme.ajax.query(url, options, data);

        var _fail = function(error, status) {
            self.fail(error, status);

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

        query.onFail(function(event, error, status) {
                  if (options.warnOnFail) {
                      var message = Object.isString(error) ? error : (error.message || gettext("Error"));
                      creme.dialogs.error(message, {title: options.warnOnFailTitle}, status)
                                   .onClose(function() {
                                        _fail(error, status);
                                    })
                                   .open();
                  } else {
                      _fail(error, status);
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

        if (options.waitingOverlay) {
            query.onStart(function() {
                      creme.utils.showPageLoadOverlay();
                  })
                 .onComplete(function() {
                      creme.utils.hidePageLoadOverlay();
                  });
        }

        if (options.confirm) {
            var confirmMessage = Object.isString(options.confirm) ? options.confirm : gettext("Are you sure ?");

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

// BEWARE: DO NOT USE THIS, BECAUSE IT WILL PROBABLY BE REMOVED IN CREME 2.1
//    (we do not deprecate it because it is still used by list-view,
//     & we do not want to pollute terminal with annoying messages)
creme.utils.innerPopupFormAction = function(url, options, data) {
    options = $.extend({
        submit_label: gettext("Save"),
        submit: function(dialog) {
            creme.utils.handleDialogSubmit(dialog);
        },
        validator: function(data) {
            return true;
        },
        reloadOnSuccess: false
    }, options || {});

    return new creme.component.Action(function() {
        var self = this;

        creme.utils.showInnerPopup(url, {
               send_button_label: options.submit_label,
               send_button: function(dialog) {
                   try {
                       var submitdata = options.submit.apply(this, arguments);

                       if (submitdata && options.validator(submitdata)) {
                           self.done(submitdata);
                           creme.utils.closeDialog(dialog, options.reloadOnSuccess);
                       }
                   } catch (e) {
                       self.fail(e);
                   }
               },
               cancel: function(event, ui) {
                   self.cancel();
               },
               close: function(event, ui) {
                   creme.utils.closeDialog($(this), false);
                   self.cancel();
               },
               closeOnEscape: options.closeOnEscape
           },
           null, {
               error: function(data, error) {
                   self.fail(data, error);
               },
               data: data
           });
    });
};

creme.utils.isHTMLDataType = function(dataType) {
    return Object.isString(dataType) &&
           ['html', 'text/html'].indexOf(dataType.toLowerCase()) !== -1;
};

/*******************************************************************************
    Taken from Underscore.js ( http://underscorejs.org/ )

    Copyright (c) 2009-2016 Jeremy Ashkenas, DocumentCloud and Investigative
    Reporters & Editors

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
*******************************************************************************/

// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
creme.utils.debounce = function(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
};

// Temporary HACK : Fix used in some <a onclick="..."> tags to prevent multiple clicks.
creme.utils.clickOnce = function(element, func) {
    element = $(element);

    if (element.is(':not(.clickonce') && Object.isFunc(func)) {
        element.addClass('clickonce');
        return func.apply(this, Array.copy(arguments).slice(2));
    } else {
        return false;
    }
};

}(jQuery));
