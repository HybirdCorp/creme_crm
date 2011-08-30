/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2010  Hybird

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

//if(typeof(creme)==undefined) creme = {};

creme.utils = {};
//creme.utils.reload = function(something){
//    console.log("creme.utils.reload("+something+")");
//    console.log("$(something).attr('location') : "+$(something).attr('location'));
//    console.log("$(something).dialog('isOpen') : "+$(something).dialog('isOpen'));
//
//    if(typeof($(something).attr('location')) === undefined)  {
//        if($(something).dialog('isOpen')) {
//            creme.utils.reloadDialog(something);
//        }
//    } else {
//        reload(something);
//    }
//}
creme.utils.openWindow = function (url, name, params) {
    if(!params || params == '' || typeof(params) == "undefined")
        params = 'menubar=no, status=no, scrollbars=yes, menubar=no, width=800, height=600';
    window[name] = window.open(url,name,params);
}


creme.utils.reload = function (w) {
    w.location.href = w.location.href;
}

creme.utils.loading = function(div_id, is_loaded, params) {
    var $div = $('#'+div_id);
    if (is_loaded) {
        $div.dialog('destroy');
    } else {
        if ($div.size() == 0) {
            $div = $('<div id="'+div_id+'" class="ui-widget-overlay" style="display:none;"></div>');
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
        $('a.ui-dialog-titlebar-close').remove();
    }
}

creme.utils.showDialog = function(text, options, div_id) {
    var $div = $('#' + div_id);

    if($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString() + Math.ceil(Math.random() * 1000000);
        $div = $('<div id="' + div_id + '"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    $div.html(text);
    //$div.append($('<input type="hidden"/>').attr('id','dialog_id').val(div_id));

    buttons = {};
    buttons[gettext("Ok")] = function() {
            $(this).dialog("close");
            /*$(this).dialog("destroy");
            $(this).remove();*/
        }

    $div.dialog(jQuery.extend({
        buttons: buttons,
        closeOnEscape: false,
        hide: 'slide',
        show: 'slide',
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

creme.utils.build_q_filter_url = function(q_filter) {
    var url_str = '';

    if (q_filter && typeof(q_filter['name']) != "undefined") {
        var name = q_filter['name'];
        var items = q_filter['items'];
        //for(var iq in items)
        for (var i = 0; i < items.length; i++) {
            var q = items[i];
            //if(typeof(q['negated'])=="undefined" || q['negated'] != "~" || q['negated'] != "") {q['negated'] = '';q.negated = '';}
            if(typeof(q['is_or'])=="undefined" || q['is_or']!=0 || q['is_or']!=1){q['is_or'] = 0;q.is_or = 0;}
            //url_str+='&'+name+'='+(typeof(q.negated)!="undefined")?q.negated:''+q.pattern+':'+q.value+','+(typeof(q.is_or)!="undefined")?q.is_or:0;
            //url_str+='&'+name+'='+q.negated+q.pattern+':'+q.value+','+q.is_or;
            url_str += '&' + name + '=' + q.pattern + ':' + q.value + ',' + q.is_or;
        }
        url_str += '&q_name=' + name;
    }
    return url_str;
}

creme.utils.build_q_value = function(field, value, is_or, is_negated) {
    return ((is_negated)?'~':'') + field + ':' + value + ',' + Number(is_or);
}

creme.utils.build_q_input = function(field, value, is_or, is_negated, name) {
    return $('<input />').attr('name',name).attr('type','hidden').val(creme.utils.build_q_value(field, value, is_or, is_negated));
}

creme.utils.tableCollapse = function($self, trigger) {//TODO: Factorise with creme.utils.tableExpand
    //TODO: Include trigger in options?
    //TODO: Make constants with tbody.collapsable, .block_icon, ... ?

    if(typeof(trigger) == "undefined"){
        trigger = true;
    }

    var table = $self.parents('table[id!=]');
    table.find('.collapsable').hide();
//    table.find('tbody.collapsable').hide();
//    table.find('tfoot.collapsable').hide();

    table.addClass('faded');
    table.find('.block_icon').css({'height': '22px'});

    if(trigger)//Sometimes triggering the event is not necessary.
    {
        table.trigger('creme-table-collapse', {action: 'hide'});
    }
}

creme.utils.tableExpand = function($self, trigger) {
    if(typeof(trigger) == "undefined"){
        trigger = true;
    }

    var table = $self.parents('table[id!=]');
    table.find('.collapsable').show();
//    table.find('tbody.collapsable').show();
//    table.find('tfoot.collapsable').show();

    table.removeClass('faded');
    table.find('.block_icon').css({'height': 'auto'});

    if(trigger)//Sometimes triggering the event is not necessary.
    {
        table.trigger('creme-table-collapse', {action: 'show'});
    }
}

creme.utils.bindToggle = function($self) {
        $self.toggle(function(e) {
            creme.utils.tableCollapse($self);
        },function(e) {
            creme.utils.tableExpand($self);
        });
    }

creme.utils.bindShowHideTbody = function() {
//    $('.table_detail_view thead').each(function() {creme.utils.bindToggle($(this));});
    $('.table_detail_view').find('.collapser').each(function() {creme.utils.bindToggle($(this));});
}


creme.utils.simpleConfirm = function(cb, msg)
{
    var buttons = {};
    buttons[gettext("Ok")] = function() {
        if(typeof(cb) != "undefined" && $.isFunction(cb))
        {
            cb();
            $(this).dialog("destroy");
            $(this).remove();
        }
    }
    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}

    creme.utils.showDialog(msg || gettext("Are you sure ?"), {buttons: buttons});
}

creme.utils.confirmBeforeGo = function(url, ajax, ajax_options) { //TODO: rename ? factorise (see ajaxDelete()) ??
    var buttons = {};

    buttons[gettext("Ok")] = function() {
            if(typeof(ajax)!="undefined" && ajax==true) {
                //$.get(href);
                var defOpts = jQuery.extend({
                    url : url,
                    data : {},
                    success : function(data, status, req) {
                        //creme.utils.showDialog(gettext("Operation done"));
                        creme.utils.reload(window); //TODO: reload listview content instead (so rename the function)
                    },
                    error : function(req, status, error) { //TODO factorise
                        if(!req.responseText || req.responseText == "") {
                            creme.utils.showDialog(gettext("Error"));
                        } else {
                            creme.utils.showDialog(req.responseText);
                        }
                    },
                    complete : function(request, textStatus) {},
                    sync : false,
                    //method: "GET",
                    parameters : undefined
                }, ajax_options);

                $.ajax(defOpts);
                $(this).dialog("destroy");
                $(this).remove();
            } else {
                window.location.href = url;
            }
        }
    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}

    //creme.utils.showDialog(msg || gettext("Are you sure ?"), {buttons: buttons});
    creme.utils.showDialog(gettext("Are you sure ?"), {buttons: buttons});
}

creme.utils.confirmSubmit = function(atag) {
    var buttons = {};

    buttons[gettext("Ok")] = function() {
                    $('form', $(atag)).submit();
                    $(this).dialog("destroy");
                    $(this).remove();
                }
    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}

    creme.utils.showDialog(gettext("Are you sure ?"), {buttons: buttons});
}

creme.utils.changeOtherNodes = function (from_id, arrayNodesIds, callback) {
    var $from_node = $('#'+from_id);

    $(arrayNodesIds).each(function() {
            callback($from_node, this);
        }
    );
}

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
    if(typeof(callback) == "function") callback(input);
}

creme.utils.loadBlock = function(url) {//TODO: move to creme.blocks
    $.ajax({
        url:      url,
        async:    false,
        type:     "GET",
        dataType: "json",
        cache:    false, // ??
        beforeSend: this.loading('loading', false),
        success:  function(data) {
                        for (var i = 0; i < data.length; ++i) {
                            var block_data = data[i];          //tuple: (block_name, block_html)
                            var block      = $(block_data[1]); //'compile' to DOM

                            $('#' + block_data[0]).replaceWith(block);
                            $(block).find('.collapser').each(function() {creme.utils.bindToggle($(this));});
                            creme.blocks.applyState(block);
                        }
                  },
      complete: this.loading('loading',true)
    });
}

if(typeof(creme.utils.stackedPopups)=="undefined") creme.utils.stackedPopups = [];//Avoid the re-declaration in case of reload of creme_utils.js

creme.utils.showInnerPopup = function(url, options, div_id, ajax_options) {
//    console.log("creme.utils.showInnerPopup("+url+","+options+","+div_id+")");

    var $div = $('#'+div_id);
    if($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString()+Math.ceil(Math.random()*1000000);
        $div = $('<div id="'+div_id+'"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    url += (url.indexOf('?') != -1) ? '&whoami='+div_id: '?whoami='+div_id;
    $.ajax(jQuery.extend({
        url: url,
        type: "GET",
        success: function(data) {
            //var data = $(data).remove('meta,title,html');
            /*$(document.body).append($('<div id="temp"></div>').append(data))
            var $temp = $('#temp');
            $temp.remove('meta,title,html');
            data = $temp.html();
            $temp.empty().remove();*/
            creme.utils.stackedPopups.push('#' + div_id);

//            console.log("On stacke : #"+div_id);
//            console.log("Etat de creme.utils.stackedPopups : ["+creme.utils.stackedPopups+"]");

            var close_button = {};
            close_button[gettext("Close")] = function() { //$(this).dialog('close');
                                                             creme.utils.closeDialog($(this), false);
                                                        }

            creme.utils.showDialog(data,
                                   jQuery.extend({
                                       buttons: close_button,
                                       close: function(event, ui) {
                                           if(options != undefined && options.beforeClose != undefined && $.isFunction(options.beforeClose)) {
                                              options.beforeClose(event, ui, $(this));
                                           }
                                           creme.utils.closeDialog($(this), false);
                                       },
                                       open: function(event, ui) {
                                            var $me = $(event.target);
                                            var $form = $('[name=inner_body]', $me).find('form');

                                            if($form.size() > 0 && (typeof(options)=="undefined"||typeof(options['send_button'])=="undefined"||options['send_button']==true)) {
                                                var buttons = $me.dialog('option', 'buttons');
                                                buttons[gettext("Send")] = function() {creme.utils.handleDialogSubmit($me);}
                                                $form.live('submit',function() {creme.utils.handleDialogSubmit($me);});

                                                /*buttons['Envoyer'] = function(){
                                                    $form = $('[name=inner_body]', $me).find('form');

                                                    var post_data = {}
                                                    var post_url = $('[name=inner_header_from_url]',$me).val();

                                                    $form.find('input[name!=], select[name!=], button[name!=], textarea[name!=]').each(function(){
                                                       var $node = $(this);
                                                       post_data[$node.attr('name')] = $node.val();
                                                    });
                                                    post_data['whoami'] = div_id;

                                                    $.ajax({
                                                          type: $form.attr('method'),
                                                          url: post_url,
                                                          data : post_data,
                                                          beforeSend : function(request){
                                                              creme.utils.loading('loading', false, {});
                                                          },
                                                          success: function(data, status)
                                                          {
                                                              data += '<input type="hidden" name="whoami" value="'+div_id+'"/>'
                                                              $('[name=inner_body]','#'+div_id).html(data);
                                                          },
                                                          error: function(request, status, error)
                                                          {
                                                                creme.utils.showDialog("<p><b>Erreur !</b></p><p>La page va être rechargée!</p>",{'title':'Erreur'});
                                                                creme.utils.sleep("reload(window)");
                                                          },
                                                          complete:function (XMLHttpRequest, textStatus) {
                                                              creme.utils.loading('loading', true, {});
                                                          }
                                                    });
                                                }*/
                                                $me.dialog('option', 'buttons', buttons);
                                            }
//                                            else if($form.size() > 0 && typeof(options)!="undefined" & typeof(options['send_button'])=="function"){
                                            else if(typeof(options)!="undefined" && typeof(options['send_button']) == "function") {
                                                var buttons = $me.dialog('option', 'buttons');
                                                buttons[options['send_button_label'] || gettext("Send")] = function(){options['send_button']($me);}
                                                $me.dialog('option', 'buttons', buttons);
                                            }
                                       }
                                       //closeOnEscape: true
                                       //help_text : "Touche Echap pour fermer."
                                   },options), div_id
           );
        },
        error : function(req, status, error){
            if(!req.responseText || req.responseText == "") {
                creme.utils.showDialog(gettext("Error during loading the page."));
            } else {
                creme.utils.showDialog(req.responseText);
            }
        }
    }, ajax_options));
    return div_id;
}

creme.utils.handleDialogSubmit = function(dialog) {
    var div_id = dialog.attr('id');
    var $form = $('[name=inner_body]', dialog).find('form');

    var post_url = $('[name=inner_header_from_url]',dialog).val();

    /* Commented 05 august 2011
    //TODO: use jquery.serialise
    var post_data = {}
    $form.find('input[name!=], select[name!=], button[name!=], textarea[name!=]').each(function() {
       var $node = $(this);
       var $node_value = $node.val();
       if($node.is(':select') && $node.is('[multiple=true]') && $node_value == null) return;
       if(!$node.is(':checkbox') && !$node.is(':radio')) post_data[$node.attr('name')] = (!$node_value || $node_value==null)? "" : $node_value;
       if($node.is(':checked') && $node.is(':radio')) post_data[$node.attr('name')] = (!$node_value || $node_value==null)? "" : $node_value;
       if($node.is(':checked') && !$node.is(':radio')) post_data[$node.attr('name')] = $node.is(':checked'); //Works if the checkbox is not required in form (99% of cases)
    });
    post_data['whoami'] = div_id;
    */

    var data = $form.serialize();
    if(data.length > 0) data += "&";
    data += "whoami="+div_id;

    $.ajax({
          type: $form.attr('method'),
          url: post_url,
//          data : post_data,
          data : data,
          beforeSend : function(request) {
              creme.utils.loading('loading', false, {});
          },
          success: function(data, status) {
              data += '<input type="hidden" name="whoami" value="'+div_id+'"/>'
              $('[name=inner_body]','#'+div_id).html(data);
              var $error_list = $('.errorlist:first', '.non_field_errors');
              if($error_list.size() > 0){
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
                                   'send_button': function($dialog) {
                                        creme.ajax.iframeSubmit(
                                            $('[name=inner_body]', $dialog).find('form'),
                                            function(data) {
                                                var div_id = $dialog.attr('id');
                                                data += '<input type="hidden" name="whoami" value="'+div_id+'"/>';
                                                $('[name=inner_body]','#'+div_id).html(data);

                                                if($('[name=is_valid]','#'+div_id).val().toLowerCase() === "true") {
                                                    creme.utils.closeDialog($('#'+div_id),true);
                                                }
                                            },
                                            {'action': $('[name=inner_header_from_url]',$dialog).val()}
                                        );
                                    }
                                });
}

creme.utils.closeDialog = function(dial, reload, beforeReloadCb, callback_url) {
//    console.log("creme.utils.closeDialog("+dial+");");
//    console.log($(dial));
//    console.log("creme.utils.closeDialog=>creme.utils.stackedPopups : "+creme.utils.stackedPopups);

    $(dial).dialog("destroy");
    $(dial).remove();
    creme.utils.stackedPopups.pop();//Remove dial from opened dialog array
//    console.log("creme.utils.stackedPopups post pop:"+creme.utils.stackedPopups);
    if(beforeReloadCb != undefined && $.isFunction(beforeReloadCb)) {
        beforeReloadCb();
    }
    // add by Jonathan 20/05/2010 in order to have a different callback url for inner popup if needs
    if(callback_url != undefined) {
        document.location = callback_url
    } else {
        if(reload) creme.utils.reloadDialog(creme.utils.stackedPopups[creme.utils.stackedPopups.length-1] || window);//Get the dial's parent dialog or window
    }
//    console.log("Etat de la stack apres le reload:"+creme.utils.stackedPopups);
}

creme.utils.reloadDialog = function(dial) {
//    console.log("creme.utils.reloadDialog("+dial+")");
    //if(dial==window) return;//reload(window);
    if(dial == window) {
        creme.utils.reload(window);
        return;
    }

    var reload_url = $(dial).find('[name=inner_header_from_url]').val();
    var div_id     = $(dial).find('[name=whoami]').val();

    reload_url += (reload_url.indexOf('?') != -1) ? '&whoami='+div_id: '?whoami='+div_id;

//    console.log("reload_url:"+reload_url);
//    console.log("div_id:"+div_id);

    $.get(
        reload_url,
        function(data){
            /*$(document.body).append($('<div id="temp"></div>').append(data));
            var $temp = $('#temp');
            $temp.remove('meta,title,html');
            data = $temp.html();
            $temp.empty().remove();*/
            $(dial).html(data);
        }
    );
}

creme.utils.sleep = function(fn, time) {
    var time = time || 3000;
    setTimeout(fn, time);
}

creme.utils.appendInUrl = function(url, strToAppend) {
    var index_get = url.indexOf('?');
    var get = "", anchor = "";

    if(index_get > -1) {
        get = url.substring(index_get, url.length);
        url = url.substring(0, index_get);
    }
    var index_anchor = url.indexOf('#');
    if(index_anchor > -1) {
        anchor = url.substring(index_anchor, url.length);
        url = url.substring(0, index_anchor);
    }

    //TODO: factorise '+ anchor' ??
    if(strToAppend.indexOf('?') > -1) {
        url += strToAppend+get.replace('?','&') + anchor;
    } else if(strToAppend.indexOf('&') > -1) {
        url += get + strToAppend + anchor;
    } else url += strToAppend + get + anchor;

    return url;
}

creme.utils.ajaxDelete = function(url, _data, ajax_params, msg) {
    var buttons = {};

    buttons[gettext("Ok")] = function() {
            var defOpts = jQuery.extend({
                url: url,
                data: _data,
                beforeSend : function(req) {
                    creme.utils.loading('loading', false);
                },
                success: function(data, status, req) {
                    creme.utils.showDialog(gettext("Suppression done"));
                },
                error: function(req, status, error) {
                    if(!req.responseText || req.responseText == "") {
                        creme.utils.showDialog(gettext("Error"));
                    } else {
                        creme.utils.showDialog(req.responseText);
                    }
                },
                complete: function(request, textStatus) {
                    creme.utils.loading('loading', true);
                },
                sync: false,
                type: "POST"
            }, ajax_params);

            $.ajax(defOpts);
            //creme.ajax.json.send(url, defOpts.data, defOpts.success_cb, defOpts.error_cb, defOpts.sync,defOpts.method,defOpts.parameters);
            $(this).dialog("destroy");
            $(this).remove();
        }
    buttons[gettext("Cancel")] = function() {$(this).dialog("destroy");$(this).remove();}

    creme.utils.showDialog(msg || gettext("Are you sure ?"), {buttons: buttons});
}

//TODO: move to a block.py (and postNReload() etc...)???
creme.utils.innerPopupNReload = function(url, reload_url) {
    creme.utils.showInnerPopup(url,
                              {
                                  beforeClose: function(event, ui, dial) {
                                                    creme.utils.loadBlock(reload_url);
                                                }
                              });
}

creme.utils.postNReload = function(url, reload_url) {
    creme.ajax.post({
                'url': url,
                'success': function(data, status) {
                      creme.utils.loadBlock(reload_url);
                    }
            });
}

creme.utils.submitNReload = function(form, reload_url, options) {
    var defaults = {
        'success': function(data, status) {
          creme.utils.loadBlock(reload_url);
        }
    }
    options = $.extend(defaults, options);
    creme.ajax.submit(form, true, options);
}

creme.utils.handleResearch = function(url, target_node_id, scope) {
    var _data = {};
    $(scope.targets).each(function() {
       _data[this] = $('[name='+this+']', scope.from).val();
    });

    $.ajax({
        url: url,
        type: 'POST',
        data: _data,
        dataType: 'html',
        success: function(data, status, req) {
            $('#' + target_node_id).html(data);
        },
        error: function(req, status, errorThrown) {
        },
        complete: function() {
            document.title = gettext("Search results...");
        }
    });
}

creme.utils.handleResearchKd = function(e, url, target_node_id, scope) {
    if (e.keyCode == '13'){
        creme.utils.handleResearch(url, target_node_id, scope);
    }
}

creme.utils.handleQuickForms = function(url, $scope_from, targets) {
    var uri = url;

    $(targets).each(function() {
        uri += '/' + $('[name=' + this + ']', $scope_from).val();
    });

    creme.utils.showInnerPopup(uri); //, {'width' : 950}
}

creme.utils.multiDeleteFromListView = function(lv_selector, delete_url) {
    if($(lv_selector).list_view('countEntities') == 0) {
        creme.utils.showDialog(gettext("Please select at least one entity."));
        return;
    }

    $(lv_selector).list_view('option', 'entity_separator', ',');

    var ajax_opts = {
        complete : function(request, textStatus) {
                            $(lv_selector).list_view('reload');
                            creme.utils.loading('loading', true);
                    }
    };
    //TODO: gettext("Are you sure ?") useless ??
    creme.utils.ajaxDelete(delete_url, {'ids' : $(lv_selector).list_view('getSelectedEntities')}, ajax_opts, gettext("Are you sure ?"));
}

creme.utils.autoCheckallState = function(from, select_all_selector, checkboxes_selector) {
    var $select_all = $(select_all_selector);

    if(!$(from).is(':checked')) {
        $select_all.uncheck();
        return;
    }

    var all_checked = true;
    $(checkboxes_selector).each(function() {
        all_checked = all_checked & $(this).is(':checked');
    });

    if(all_checked) {
        $select_all.check();
    } else {
        $select_all.uncheck();
    }
};

creme.utils.toggleCheckallState = function(select_all, checkboxes_selector) {
    if($(select_all).is(':checked')) {
        $(checkboxes_selector).check();
    } else {
        $(checkboxes_selector).uncheck();
    }
};

//TODO: rename (goTo ??)
creme.utils.go_to = function(url, ajax, ajax_options) {
    if(typeof(ajax) != "undefined" && ajax) {
        if(typeof(ajax_options) != "undefined" && ajax_options) {
            $(ajax_options.target).load(url, ajax_options.data, ajax_options.complete);
        } else {
            $("#sub_content").load(url, {}, null);
        }
    } else {
        window.location.href = url;
    }
}

creme.utils.range = function(start, end) {
    var tab = [];
    for(var i=start||0; i < end; i++) {
        tab.push(i);
    }

    return tab;
};

creme.utils.HEXtoRGB = function(hex){//Extracted from gccolor-1.0.3 plugin
    var hex = parseInt(((hex.indexOf('#') > -1) ? hex.substring(1) : hex), 16);
    return {r: hex >> 16, g: (hex & 0x00FF00) >> 8, b: (hex & 0x0000FF)};
};

creme.utils.RGBtoHSB = function(rgb){
    var hsb = {};
    hsb.b = Math.max(Math.max(rgb.r, rgb.g), rgb.b);
    hsb.s = (hsb.b <= 0) ? 0 : Math.round(100 * (hsb.b - Math.min(Math.min(rgb.r, rgb.g), rgb.b)) / hsb.b);
    hsb.b = Math.round((hsb.b / 255) * 100);
    if((rgb.r == rgb.g) && (rgb.g == rgb.b)) hsb.h = 0;
    else if(rgb.r >= rgb.g && rgb.g >= rgb.b) hsb.h = 60 * (rgb.g - rgb.b) / (rgb.r - rgb.b);
    else if(rgb.g >= rgb.r && rgb.r >= rgb.b) hsb.h = 60  + 60 * (rgb.g - rgb.r) / (rgb.g - rgb.b);
    else if(rgb.g >= rgb.b && rgb.b >= rgb.r) hsb.h = 120 + 60 * (rgb.b - rgb.r) / (rgb.g - rgb.r);
    else if(rgb.b >= rgb.g && rgb.g >= rgb.r) hsb.h = 180 + 60 * (rgb.b - rgb.g) / (rgb.b - rgb.r);
    else if(rgb.b >= rgb.r && rgb.r >= rgb.g) hsb.h = 240 + 60 * (rgb.r - rgb.g) / (rgb.b - rgb.g);
    else if(rgb.r >= rgb.b && rgb.b >= rgb.g) hsb.h = 300 + 60 * (rgb.r - rgb.b) / (rgb.r - rgb.g);
    else hsb.h = 0;
    hsb.h = Math.round(hsb.h);
    return hsb;
};

creme.utils.showErrorNReload = function() {
    creme.utils.showDialog('<p><b>' + gettext("Error !") + '</b></p><p>' + gettext("The page will be reload !") + '</p>',
                                       {'title': gettext("Error")});
    creme.utils.sleep("creme.utils.reload(window)");
};

creme.utils.scrollTo = function($elements) {
//    var $element = $elements.first(); //jQuery >= 1.4
    var $element = $elements.eq(0);
    if($element.size() == 1) {
        var elementPos = $element.position();
        scrollTo(elementPos.left, elementPos.top);
    }
}
