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

creme.utils = {};

creme.utils.openWindow = function (url, name, params) {
    window[name] = window.open(url, name, params || 'menubar=no, status=no, scrollbars=yes, menubar=no, width=800, height=600');
}

creme.utils.reload = function (w) {
    w.location.href = w.location.href;
}

creme.utils.loading = function(div_id, is_loaded, params) {
    var $div = $('#' + div_id);
    if (is_loaded) {
        $div.dialog('destroy');
        $div.remove();//Clean
    } else {
        if ($div.size() == 0) {
            $div = $('<div id="' + div_id + '" class="ui-widget-overlay" style="display:none;"></div>');
            $(document.body).append($div);
        }
        $div.dialog(jQuery.extend({
                buttons: {},
                closeOnEscape: false,
                title: '<img src="' + creme_media_url("images/wait.gif") + '"/>' + gettext("Loading..."),
                modal: true,
                resizable: false,
                draggable: false,
                dialogClass: ''
        }, params));
        $div.css({'min-height': 0, 'height': 0, 'padding': 0});
        $('a.ui-dialog-titlebar-close').remove();
    }
}

creme.utils.showDialog = function(text, options, div_id) {
    var $div = $('#' + div_id);

    if ($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString() + Math.ceil(Math.random() * 1000000);
        $div = $('<div id="' + div_id + '"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    $div.html(text);

    $div.dialog(jQuery.extend({
        buttons: [{text: gettext("Ok"),
                   click: function() {
                            $(this).dialog("close");
                   }
                 }
        ],
        closeOnEscape: false,
        /*hide: 'slide',
        show: 'slide',*/
        title: '',
        modal: true,
        width:'auto',
        close: function(event, ui) {
                $(this).dialog("destroy");
                $(this).remove();
        }
    }, options));

    /*if(typeof(options['help_text'])!="undefined")
    {
        $('a.ui-dialog-titlebar-close').clone(true)
                                       .appendTo($('a.ui-dialog-titlebar-close').parent())
                                       .children('span')
                                       .removeClass('ui-icon-closethick')
                                       .addClass('ui-icon-info')
                                       .css('margin-right','1em')
    }*/
}

// creme.utils.build_q_filter_url = function(q_filter) {
//     var url_str = '';
// 
//     if (q_filter && typeof(q_filter['name']) != "undefined") {
//         var name = q_filter['name'];
//         var items = q_filter['items'];
//         //for(var iq in items)
//         for (var i = 0; i < items.length; i++) {
//             var q = items[i];
//             //if(typeof(q['negated'])=="undefined" || q['negated'] != "~" || q['negated'] != "") {q['negated'] = '';q.negated = '';}
//             if(typeof(q['is_or'])=="undefined" || q['is_or']!=0 || q['is_or']!=1){q['is_or'] = 0;q.is_or = 0;}
//             //url_str+='&'+name+'='+(typeof(q.negated)!="undefined")?q.negated:''+q.pattern+':'+q.value+','+(typeof(q.is_or)!="undefined")?q.is_or:0;
//             //url_str+='&'+name+'='+q.negated+q.pattern+':'+q.value+','+q.is_or;
//             url_str += '&' + name + '=' + q.pattern + ':' + q.value + ',' + q.is_or;
//         }
//         url_str += '&q_name=' + name;
//     }
//     return url_str;
// }

// creme.utils.build_q_value = function(field, value, is_or, is_negated) {//TODO: Still used?
//     return ((is_negated)?'~':'') + field + ':' + value + ',' + Number(is_or);
// }

// creme.utils.build_q_input = function(field, value, is_or, is_negated, name) {
//     return $('<input />').attr('name',name).attr('type','hidden').val(creme.utils.build_q_value(field, value, is_or, is_negated));
// }

creme.utils.tableExpandState = function($self, state, trigger) {
    var $table = $self.parents('table[id!=]');
    var $collapsable = $table.find('.collapsable');

    var old_state = !$table.hasClass('collapsed');

    if (state === old_state)
        return;

    $table.toggleClass('collapsed faded', !state);

    if (trigger === undefined || trigger) {
        $table.trigger('creme-table-collapse', {action: state ? 'show' : 'hide'});
    }
}

creme.utils.tableIsCollapsed = function($self) {
    return $self.parents('table[id!=]').hasClass('collapsed');
}

creme.utils.tableExpand = function($self, trigger) {
    creme.utils.tableExpandState($self, true, trigger);
}

creme.utils.bindTableToggle = function($self) {
    $self.click(function(e) {
        creme.utils.tableExpandState($self, creme.utils.tableIsCollapsed($self));
    });
}

creme.utils.bindShowHideTbody = function() {
//    $('.table_detail_view thead').each(function() {creme.utils.bindToggle($(this));});
    $('.table_detail_view').find('.collapser').each(function() {
        creme.utils.bindTableToggle($(this));
    });
}

creme.utils.simpleConfirm = function(cb, msg) {
    var buttons = [{
                        text: gettext("Ok"),
                        click: function() {
                            cb();
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   },
                   {
                        text: gettext("Cancel"),
                        click: function() { //TODO: factorise
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   }
    ];

    creme.utils.showDialog(msg || gettext("Are you sure ?"), {buttons: buttons});
}

creme.utils.confirmBeforeGo = function(url, ajax, ajax_options) { //TODO: factorise (see ajaxDelete()) ??
    var buttons = [{
                        text: gettext("Ok"),
                        click: function() {
                            if (ajax) {
                                $.ajax(jQuery.extend({
                                            url: url,
                                            data: {},
                                            success: function(data, status, req) {
                                                creme.utils.reload(window); //TODO: reload listview content instead (so rename the function)
                                            },
                                            error: function(req, status, error) {
                                                creme.utils.showDialog(req.responseText || gettext("Error"));
                                            },
                                            complete: function(request, textStatus) {},
                                            sync: false,
                                            //method: "GET",
                                            parameters : undefined
                                        }, ajax_options)
                                );
                                $(this).dialog("destroy");
                                $(this).remove();
                            } else {
                                window.location.href = url;
                            }
                        }
                   },
                   {
                        text: gettext("Cancel"),
                        click: function() { //TODO: factorise
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   }
    ];

    creme.utils.showDialog(gettext("Are you sure ?"), {buttons: buttons});
}

creme.utils.confirmSubmit = function(atag) {
    var buttons = [{
                        text: gettext("Ok"),
                        click: function() {
                            $('form', $(atag)).submit();
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   },
                   {
                        text: gettext("Cancel"),
                        click: function() { //TODO: factorise
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   }
    ];

    creme.utils.showDialog(gettext("Are you sure ?"), {buttons: buttons});
}

// creme.utils.changeOtherNodes = function (from_id, arrayNodesIds, callback) {
//     var $from_node = $('#'+from_id);
// 
//     $(arrayNodesIds).each(function() {
//             callback($from_node, this);
//         }
//     );
// }

//TODO: move to assistants.js ??
creme.utils.validateEntity = function(form, checkbox_id, reload_url) {
    var checked = document.getElementById(checkbox_id);
    if (checked.checked == false) {
        creme.utils.showDialog('<p>' + gettext("Check the box if you consider as treated") + '</p>',
                               {'title': gettext("Error")}, 'error');
    } else {
//        form.submit();
        creme.ajax.submit(form, {}, {'success': function(){creme.utils.loadBlock(reload_url);}});
    }
}

creme.utils.handleSort = function(sort_field, sort_order, new_sort_field, input, callback) {
    var $sort_field = $(sort_field);
    var $sort_order = $(sort_order);

    if($sort_field.val() == new_sort_field) {
        if($sort_order.val() == "") {
            $sort_order.val("-");
        } else {
            $sort_order.val("");
        }
    } else {
        $sort_order.val("");
    }
    $sort_field.val(new_sort_field);
//     if(typeof(callback) == "function") callback(input);
    if ($.isFunction(callback))
        callback(input);
}

if(typeof(creme.utils.stackedPopups)=="undefined") creme.utils.stackedPopups = [];//Avoid the re-declaration in case of reload of creme_utils.js

creme.utils.showInnerPopup = function(url, options, div_id, ajax_options, reload) {
    var reload_on_close = creme.object.isTrue(reload);

    var $div = $('#' + div_id);
    if ($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString() + Math.ceil(Math.random() * 1000000);
        $div = $('<div id="' + div_id + '"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    url += (url.indexOf('?') != -1) ? '&whoami=' + div_id: '?whoami=' + div_id; //TODO: use jquery method that builds URLs ?
    $.ajax(jQuery.extend({
        url: url,
        type: "GET",
        success: function(data) {
            creme.utils.stackedPopups.push('#' + div_id);
            creme.utils.showDialog(data,
                                   jQuery.extend({
                                       buttons: [{text: gettext("Cancel"),
                                                  click: function() { //$(this).dialog('close');
                                                             if (options !== undefined && $.isFunction(options.cancel)) {
                                                                 options.cancel($(this));
                                                             }

                                                             creme.utils.closeDialog($(this), reload_on_close);
                                                        }
                                                 }
                                                ],
                                       close: function(event, ui) {
                                           creme.utils.closeDialog($(this), false);
                                       },
                                       open: function(event, ui) {
                                            var $me = $(event.target);
                                            var $form = $('[name=inner_body]', $me).find('form');

                                            if (options === undefined) //TODO: move this code in the start of the function ?
                                                options = {};

                                            var send_button = options['send_button']; //function or boolean (if defined)

                                            if ($form.size() || send_button) {
                                                var submit_handler;

                                                if ($.isFunction(send_button))
                                                    submit_handler = function() {send_button($me);};
                                                else
                                                    submit_handler = function() {creme.utils.handleDialogSubmit($me);};

                                                //$form.live('submit', function() {creme.utils.handleDialogSubmit($me);});

                                                var buttons = $me.dialog('option', 'buttons');
                                                //TODO: use the OS order for 'Cancel'/'OK' buttons
                                                buttons.unshift({text: options['send_button_label'] || gettext("Save"),
                                                                 click: submit_handler
                                                                }
                                                               );
                                                $me.dialog('option', 'buttons', buttons);
                                            }
                                       }
                                       //closeOnEscape: true
                                       //help_text : "Tape Escape to close."
                                   },options), div_id
           );
        },
        error: function(req, status, error) {
//             if (!req.responseText || req.responseText == "") {
//                 creme.utils.showDialog(gettext("Error during loading the page."));
//             } else {
//                 creme.utils.showDialog(req.responseText);
//             }
            creme.utils.showDialog(req.responseText || gettext("Error during loading the page."));
        }
    }, ajax_options));

    return div_id;
}

creme.utils.handleDialogSubmit = function(dialog) {
    var div_id = dialog.attr('id');
    var $form = $('[name=inner_body]', dialog).find('form');
    var post_url = $('[name=inner_header_from_url]', dialog).val();

    var data = $form.serialize();
    if (data.length > 0) data += "&";
    data += "whoami=" + div_id;

    $.ajax({
          type: $form.attr('method'),
          url: post_url,
//          data : post_data,
          data: data,
          beforeSend: function(request) {
              creme.utils.loading('loading', false, {});
          },
          success: function(data, status) {
              data += '<input type="hidden" name="whoami" value="' + div_id + '"/>'
              $('[name=inner_body]', '#' + div_id).html(data);

              creme.widget.shutdown($('[name=inner_body]', '#' + div_id));

              var $error_list = $('.errorlist:first', '.non_field_errors');

              if ($error_list.size() > 0){
                var err_pos = $error_list.position();
                scrollTo(err_pos.left, err_pos.top);
              }

          },
          error: function(request, status, error) {
            creme.utils.showErrorNReload();
          },
          complete:function (XMLHttpRequest, textStatus) {
              creme.utils.loading('loading', true, {});
          }
    });

    return false;
}

creme.utils.iframeInnerPopup = function(url) {
    creme.utils.showInnerPopup(url,
                               {
                                   send_button: function($dialog) {
                                        creme.ajax.jqueryFormSubmit(
                                            $('[name=inner_body]', $dialog).find('form'),
                                            function(data) {
                                                var div_id = $dialog.attr('id');
                                                var body = $('[name=inner_body]', $dialog);
                                                var data = $(data);

                                                body.empty();
                                                body.append(data);
                                                body.append($('<input type="hidden" name="whoami">').val(div_id));

                                                if (data.attr('closing') !== undefined) {
                                                    creme.utils.closeDialog($dialog, true);
                                                }
                                            },
                                            function(error) {
                                                creme.utils.closeDialog($dialog, true);
                                                creme.utils.showErrorNReload();
                                            },
                                            {action: $('[name=inner_header_from_url]', $dialog).val()}
                                        );
                                    }
                                });
}

creme.utils.closeDialog = function(dial, reload, beforeReloadCb, callback_url) {
    $(dial).dialog("destroy");

    creme.widget.shutdown($(dial));
    $(dial).remove();

    creme.utils.stackedPopups.pop();//Remove dial from opened dialog array

//     if (beforeReloadCb != undefined && $.isFunction(beforeReloadCb)) {
    if ($.isFunction(beforeReloadCb))
        beforeReloadCb();

    // add by Jonathan 20/05/2010 in order to have a different callback url for inner popup if needs
    if (callback_url != undefined) {
        document.location = callback_url;
    } else if(reload) {
        creme.utils.reloadDialog(creme.utils.stackedPopups[creme.utils.stackedPopups.length-1] || window);//Get the dial's parent dialog or window
    }
}

creme.utils.reloadDialog = function(dial) {
    if (dial == window) {
        creme.utils.reload(window);
        return;
    }

    var reload_url = $(dial).find('[name=inner_header_from_url]').val();
    var div_id     = $(dial).find('[name=whoami]').val();

    reload_url += (reload_url.indexOf('?') != -1) ? '&whoami=' + div_id:
                                                    '?whoami=' + div_id;

    $.get(reload_url, function(data) { $(dial).html(data); });
}

creme.utils.sleep = function(fn, time) {
    setTimeout(fn, time || 3000);
}

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
        url += strToAppend+get.replace('?', '&');
    } else if (strToAppend.indexOf('&') > -1) {
        url += get + strToAppend;
    } else url += strToAppend + get;

    return url + anchor;
}

creme.utils.ajaxDelete = function(url, _data, ajax_params, msg) {
    //TODO: order of the OS for the buttons
    var buttons = [{
                        text: gettext("Ok"), //TODO: improve message ('Delete', 'Unlink'...)
                        click: function() {
                            var options = jQuery.extend({
                                url: url,
                                data: _data,
                                beforeSend: function(req) {
                                    creme.utils.loading('loading', false);
                                },
                                error: function(req, status, error) {
//                                     if(!req.responseText || req.responseText == "") {
//                                         creme.utils.showDialog(gettext("Error"));
//                                     } else {
//                                         creme.utils.showDialog(req.responseText);
//                                     }
                                    creme.utils.showDialog(req.responseText || gettext("Error"));
                                },
                                complete: function(request, textStatus) {
                                    creme.utils.loading('loading', true);
                                },
                                sync: false,
                                type: "POST"
                            }, ajax_params);

                            $.ajax(options);
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   },
                   {
                        text: gettext("Cancel"),
                        click: function() {
                            $(this).dialog("destroy");
                            $(this).remove();
                        }
                   }
        ];

    creme.utils.showDialog(msg || gettext("Are you sure ?"), {buttons: buttons});
}

//TODO: move to a block.py (and postNReload() etc...)???
creme.utils.innerPopupNReload = function(url, reload_url) {
    creme.utils.showInnerPopup(url, {
        beforeClose: function(event, ui, dial) {
            creme.utils.loadBlock(reload_url);
        }
    });
}

creme.utils.postNReload = function(url, reload_url) {
    creme.ajax.post({
        url: url,
        success: function(data, status) {
            creme.utils.loadBlock(reload_url);
        }
    });
}

creme.utils.submitNReload = function(form, reload_url, options) {
    var defaults = {
        success: function(data, status) {
          creme.utils.loadBlock(reload_url);
        }
    }
    creme.ajax.submit(form, true, $.extend(defaults, options));
}

creme.utils.handleResearch = function(target_node_id, from) {
    var research =  $('[name=research]', from).val();

    $.ajax({
        url: '/creme_core/search',
        type: 'POST',
        data: {
                ct_id:    $('[name=ct_id]', from).val(),
                research: research
        },
        dataType: 'html',
        success: function(data, status, req) {
            $('#' + target_node_id).html(data);

            //highlight the word that we are searching
            research = research.toLowerCase();
            $('div.result').find("td, td *")
                           .contents()
                           .filter(function() {
                                    if(this.nodeType != Node.TEXT_NODE) return false;
                                    return this.textContent.toLowerCase().indexOf(research) >= 0;
                                })
                           .wrap($('<mark/>'));
        },
        error: function(req, status, errorThrown) {
        },
        complete: function() {
            document.title = gettext("Search results...");
        }
    });
}

creme.utils.handleQuickForms = function(url, $scope_from, targets) {
    var uri = url;

    $(targets).each(function() {
        uri += '/' + $('[name=' + this + ']', $scope_from).val();
    });

    //creme.utils.showInnerPopup(uri); //, {'width' : 950}
    creme.utils.iframeInnerPopup(uri);
}

creme.utils.multiDeleteFromListView = function(lv_selector, delete_url) {
    if ($(lv_selector).list_view('countEntities') == 0) {
        creme.utils.showDialog(gettext("Please select at least one entity."));
        return;
    }

    $(lv_selector).list_view('option', 'entity_separator', ',');

    var ajax_opts = {
        complete: function(request, textStatus) {
                        $(lv_selector).list_view('reload');
                        creme.utils.loading('loading', true);
                  }
    };
    //TODO: gettext("Are you sure ?") useless ??
    creme.utils.ajaxDelete(delete_url, {ids: $(lv_selector).list_view('getSelectedEntities')}, ajax_opts, gettext("Are you sure ?"));
}

creme.utils.autoCheckallState = function(from, select_all_selector, checkboxes_selector) {
    var $select_all = $(select_all_selector);

    if (!$(from).is(':checked')) {
        $select_all.uncheck();
        return;
    }

    var all_checked = true;
    $(checkboxes_selector).each(function() {
        all_checked = all_checked & $(this).is(':checked');
    });

    if (all_checked) {
        $select_all.check();
    } else {
        $select_all.uncheck();
    }
};

creme.utils.toggleCheckallState = function(select_all, checkboxes_selector) {
    if ($(select_all).is(':checked')) {
        $(checkboxes_selector).check();
    } else {
        $(checkboxes_selector).uncheck();
    }
};

//TODO: rename (goTo ??)
creme.utils.go_to = function(url, ajax, ajax_options) {
//     if(typeof(ajax) != "undefined" && ajax) {
    if (ajax) { // TODO: seems unused
//         if(typeof(ajax_options) != "undefined" && ajax_options) {
        if (ajax_options) {
            $(ajax_options.target).load(url, ajax_options.data, ajax_options.complete);
        } else {
            $("#sub_content").load(url, {}, null);
        }
    } else {
        window.location.href = url;
    }
}

creme.utils.range = function(start, end) { //TODO: useful ?? (only by creme.graphael)
    var tab = [];
    for (var i=start||0; i < end; i++) {
        tab.push(i);
    }

    return tab;
};

creme.utils.HEXtoRGB = function(hex) {//Extracted from gccolor-1.0.3 plugin
    var hex = parseInt(((hex.indexOf('#') > -1) ? hex.substring(1) : hex), 16);
    return {r: hex >> 16, g: (hex & 0x00FF00) >> 8, b: (hex & 0x0000FF)};
};

// XXX: commented the 13th october 2013
// creme.utils.RGBtoHSB = function(rgb) {
//     var hsb = {};
//     hsb.b = Math.max(Math.max(rgb.r, rgb.g), rgb.b);
//     hsb.s = (hsb.b <= 0) ? 0 : Math.round(100 * (hsb.b - Math.min(Math.min(rgb.r, rgb.g), rgb.b)) / hsb.b);
//     hsb.b = Math.round((hsb.b / 255) * 100);
//     if((rgb.r == rgb.g) && (rgb.g == rgb.b)) hsb.h = 0;
//     else if(rgb.r >= rgb.g && rgb.g >= rgb.b) hsb.h = 60 * (rgb.g - rgb.b) / (rgb.r - rgb.b);
//     else if(rgb.g >= rgb.r && rgb.r >= rgb.b) hsb.h = 60  + 60 * (rgb.g - rgb.r) / (rgb.g - rgb.b);
//     else if(rgb.g >= rgb.b && rgb.b >= rgb.r) hsb.h = 120 + 60 * (rgb.b - rgb.r) / (rgb.g - rgb.r);
//     else if(rgb.b >= rgb.g && rgb.g >= rgb.r) hsb.h = 180 + 60 * (rgb.b - rgb.g) / (rgb.b - rgb.r);
//     else if(rgb.b >= rgb.r && rgb.r >= rgb.g) hsb.h = 240 + 60 * (rgb.r - rgb.g) / (rgb.b - rgb.g);
//     else if(rgb.r >= rgb.b && rgb.b >= rgb.g) hsb.h = 300 + 60 * (rgb.r - rgb.b) / (rgb.r - rgb.g);
//     else hsb.h = 0;
//     hsb.h = Math.round(hsb.h);
//     return hsb;
// };

creme.utils.luminance = function(r, g, b) {
    r = Math.pow (r / 255, 2.2);
    g = Math.pow (g / 255, 2.2);
    b = Math.pow (b / 255, 2.2);

    return 0.212671*r + 0.715160*g + 0.072169*b;
};

creme.utils.contrast = function(r, g, b, r2, g2, b2) {
    var luminance1 = creme.utils.luminance(r, g, b);
    var luminance2 = creme.utils.luminance(r2, g2, b2);
    return (Math.max(luminance1, luminance2) + 0.05) / (Math.min(luminance1, luminance2) + 0.05);
};

creme.utils.maxContrastingColor = function(r, g, b) {
    var withWhite = creme.utils.contrast(r, g, b, 255, 255, 255);
    var withBlack = creme.utils.contrast(r, g, b, 0, 0, 0);

    if (withWhite > withBlack)
        return 'white';
    return 'black'; //TODO: ? 'white': 'black';
};

creme.utils.showErrorNReload = function() {
    creme.utils.showDialog('<p><b>' + gettext("Error !") + '</b></p><p>' + gettext("The page will be reload !") + '</p>',
                           {'title': gettext("Error")}
                          );
    creme.utils.sleep("creme.utils.reload(window)");
};

creme.utils.scrollTo = function($elements) {
    var $element = $elements.first();

    if ($element.size() == 1) {
        var elementPos = $element.position();
        scrollTo(elementPos.left, elementPos.top);
    }
}
