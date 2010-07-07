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

function openWindow(url, name, params)
{
    if(!params || params == '' || typeof(params) == "undefined")
        params = 'menubar=no, status=no, scrollbars=yes, menubar=no, width=800, height=600';
    window[name] = window.open(url,name,params);
}

function reload(w)
{
    w.location.href=w.location.href;
}

//if(typeof(creme)==undefined) creme = {};

creme.utils = {};
//creme.utils.reload = function(something){
//    console.log("creme.utils.reload("+something+")");
//    console.log("$(something).attr('location') : "+$(something).attr('location'));
//    console.log("$(something).dialog('isOpen') : "+$(something).dialog('isOpen'));
//
//    if(typeof($(something).attr('location')) === undefined)
//    {
//        if($(something).dialog('isOpen'))
//        {
//            creme.utils.reloadDialog(something);
//        }
//    }
//    else
//    {
//        reload(something);
//    }
//}

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
                title: '<img src="/site_media/images/wait.gif"/> Chargement...',
                modal: true,
                resizable: false,
                draggable: false,
                dialogClass: ''
        }, params));
        $('a.ui-dialog-titlebar-close').remove();
    }
}

creme.utils.showDialog = function(text, options, div_id) {
    var $div = $('#'+div_id);
    if($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString()+Math.ceil(Math.random()*1000000);
        $div = $('<div id="'+div_id+'"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    $div.html(text);
    //$div.append($('<input type="hidden"/>').attr('id','dialog_id').val(div_id));
    $div.dialog(jQuery.extend({
        buttons: {
            "Ok": function() {
                $(this).dialog("close");
                /*$(this).dialog("destroy");
                $(this).remove();*/
            }
        },
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

/* Fonction permettant de
 * rechercher les doublons dans un tableau js a une dimension
 * Code original modifié :
 * http://www.asp-php.net/ressources/codes/JavaScript-Supprimer+les+doublons+d%27un+tableau+en+javascript.aspx
 *
 */
creme.utils.hasDoublons = function(TabInit) {
    var q = 0;
    var LnChaine = TabInit.length;
    for(x = 0; x < LnChaine; x++) {
        for(i = 0; i < LnChaine; i++) {
            if(TabInit[x] == TabInit[i] && x != i) return true;
        }
    }
    return false;
}

creme.utils.build_q_filter_url = function(q_filter) {
    var url_str = '';

    if (q_filter && typeof(q_filter['name'])!="undefined") {
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
    return ((is_negated)?'~':'')+field+':'+value+','+Number(is_or);
}

creme.utils.build_q_input = function(field, value, is_or, is_negated, name) {
    return $('<input />').attr('name',name).attr('type','hidden').val(creme.utils.build_q_value(field, value, is_or, is_negated));
}

creme.utils.bindToggle = function(self) {
        $(self).toggle(function(e) {
            var table = $(self).parents('table');
            table.find('tbody.collapsable').hide();
            table.find('tfooter.collapsable').hide();
        },function(e) {
            var table = $(self).parents('table');
            table.find('tbody.collapsable').show();
            table.find('tfooter.collapsable').show();
        });
    }

creme.utils.bindShowHideTbody = function() {
    $('.table_detail_view thead').each(function() {creme.utils.bindToggle($(this));});
}

//TODO: Remove evt argument, a argument?
creme.utils.confirmDelete = function(evt, a, msg, ajax, ajax_options) {
    evt.preventDefault();
    var href = $(a).attr('href');
    creme.utils.showDialog(msg || "Êtes-vous sûr ?",
    {
        buttons: {
            "Ok": function() {
                if(typeof(ajax)!="undefined" && ajax==true)
                {
                    //$.get(href);
                    var defOpts = jQuery.extend({
                        url : href,
                        data : {},
                        success : function(data, status, req){
                            creme.utils.showDialog("Suppression effectuée");
                        },
                        error : function(req, status, error){
                            creme.utils.showDialog("Erreur");
                        },
                        complete : function(request, textStatus){},
                        sync : false,
                        method:"GET",
                        parameters : undefined
                    }, ajax_options);

                    $.ajax(defOpts);
                    //creme.ajax.json.send(href, defOpts.data, defOpts.success_cb, defOpts.error_cb, defOpts.sync,defOpts.method,defOpts.parameters);
                    $(this).dialog("destroy");
                    $(this).remove();
                }
                else
                {
                    window.location.href=href;
                }
            },
            "Annuler": function() {$(this).dialog("destroy");$(this).remove();}
        }
    });

}

creme.utils.changeOtherNodes = function (from_id, arrayNodesIds, callback) {
    var $from_node = $('#'+from_id);

    $(arrayNodesIds).each(function() {
            callback($from_node, this);
        }
    );
}

creme.utils.fillNode = function(from_node, to_node) {
    $.ajax({
        url: "/creme_core/entity/get_repr/",
        type: "POST",
        data: {'model': to_node.model, 'pk': from_node.val(), 'field': to_node.field},
        dataType: "json",
        success: function(data){
            $('#' + to_node.id).val(data[to_node.field]);
        }
    });
}

creme.utils.renderEntity = function(from_node, to_node) {
    var pk = from_node.val();
    if(pk && !isNaN(parseInt(pk)) && pk!=0)
    $.ajax({
        url: "/creme_core/entity/render",
        type: "POST",
        data: {'model': to_node.model, 'pk': pk, 'template':to_node.template},
        dataType: "json",
        success: function(datas){
            from_node.parent().find('div').remove();
            var $div = $('<div></div>');
            $div.append($(datas));
            from_node.parent().append($div);
        }
    });
}

creme.utils.validateEntity = function(form, checkbox_id) {
    var checked = document.getElementById(checkbox_id);
    if (checked.checked == false) {
        creme.utils.showDialog("<p>Merci de <b>cocher</b> si vous considérez comme traité !</p>", {'title':'Erreur'}, 'error');
    } else {
        form.submit();
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

creme.utils.loadBlock = function(url) {
    $.ajax({
        url:      url,
        async:    true,
        type:     "GET",
        dataType: "json",
        cache:    false, // ??
//      beforeSend: loading(false), //UNCOMMENT ???
        success:  function(data) {
                        for (var i = 0; i < data.length; ++i) {
                            var block_data = data[i];          //tuple: (block_name, block_html)
                            var block      = $(block_data[1]); //'compile' to DOM

                            $('#' + block_data[0]).replaceWith(block);
                            $('thead', block).each(function() {creme.utils.bindToggle($(this));});
                        }
                  }//,
//      complete: loading(true) //UNCOMMENT ???
    });
}

if(typeof(creme.utils.stackedPopups)=="undefined") creme.utils.stackedPopups = [];//Avoid the re-declaration in case of reload of creme_utils.js
creme.utils.showInnerPopup = function(url, options, div_id){
    
//    console.log("creme.utils.showInnerPopup("+url+","+options+","+div_id+")");

    var $div = $('#'+div_id);
    if($div.size() == 0) {
        var d = new Date();
        div_id = d.getTime().toString()+Math.ceil(Math.random()*1000000);
        $div = $('<div id="'+div_id+'"  style="display:none;"></div>');
        $(document.body).append($div);
    }
    url += (url.indexOf('?') != -1) ? '&whoami='+div_id: '?whoami='+div_id;
    $.get(
        url,
        function(data){
            //var data = $(data).remove('meta,title,html');
            /*$(document.body).append($('<div id="temp"></div>').append(data))
            var $temp = $('#temp');
            $temp.remove('meta,title,html');
            data = $temp.html();
            $temp.empty().remove();*/
            creme.utils.stackedPopups.push('#'+div_id);

//            console.log("On stacke : #"+div_id);
//            console.log("Etat de creme.utils.stackedPopups : ["+creme.utils.stackedPopups+"]");
            
            creme.utils.showDialog(data,
                                   jQuery.extend({
                                       buttons: {"Fermer":function() {
                                                                        //$(this).dialog('close');
                                                                        creme.utils.closeDialog($(this), false);
                                                            }
                                                 },
                                       close: function(event, ui) {
                                           if(options != undefined && options.beforeClose != undefined && $.isFunction(options.beforeClose))
                                           {
                                              options.beforeClose(event, ui, $(this));
                                           }
                                           creme.utils.closeDialog($(this), false);
                                       },
                                       open: function(event, ui) {
                                            var $me = $(event.target);
                                            var $form = $('[name=inner_body]', $me).find('form');
                                            
                                            if($form.size() > 0 && (typeof(options)=="undefined"||typeof(options['send_button'])=="undefined"||options['send_button']==true))
                                            {
                                                var buttons = $me.dialog('option', 'buttons');
                                                buttons['Envoyer'] = function(){creme.utils.handleDialogSubmit($me);}
                                                $form.live('submit',function(){creme.utils.handleDialogSubmit($me);});
                                                
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
                                            else if(typeof(options)!="undefined" && typeof(options['send_button'])=="function"){
                                                var buttons = $me.dialog('option', 'buttons');
                                                buttons[options['send_button_label']||'Envoyer'] = function(){options['send_button']($me);}
                                                $me.dialog('option', 'buttons', buttons);

                                            }
                                       }
                                       //closeOnEscape: true
                                       //help_text : "Touche Echap pour fermer."
                                   },options), div_id
           );
        }
    );
    return div_id;
}

creme.utils.handleDialogSubmit = function(dialog){
    
    var div_id = dialog.attr('id');
    var $form = $('[name=inner_body]', dialog).find('form');

    var post_data = {}
    var post_url = $('[name=inner_header_from_url]',dialog).val();

    $form.find('input[name!=], select[name!=], button[name!=], textarea[name!=]').each(function(){
       var $node = $(this);
       if(!$node.is(':checkbox')) post_data[$node.attr('name')] = $node.val();
       if($node.is(':checked')) post_data[$node.attr('name')] = $node.is(':checked'); //Works if the checkbox is not required in form (99% of cases)
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
    return false;
}

creme.utils.iframe_inner_popup = function(url){
    creme.utils.showInnerPopup(url,
                               {
                                   'send_button': function($dialog){
                                        creme.ajax.iframe_submit
                                        (
                                            $('[name=inner_body]', $dialog).find('form'),
                                            function(data) {
                                                var div_id = $dialog.attr('id');
                                                data += '<input type="hidden" name="whoami" value="'+div_id+'"/>';
                                                $('[name=inner_body]','#'+div_id).html(data);
                                                
                                                if($('[name=is_valid]','#'+div_id).val().toLowerCase() === "true")
                                                {
                                                    creme.utils.closeDialog($('#'+div_id),true);
                                                }
                                            },
                                            {'action': $('[name=inner_header_from_url]',$dialog).val()}
                                        );
                                    }
                                });

}

creme.utils.closeDialog = function(dial, reload, beforeReloadCb, callback_url){
//    console.log("creme.utils.closeDialog("+dial+");");
//    console.log($(dial));
//    console.log("creme.utils.closeDialog=>creme.utils.stackedPopups : "+creme.utils.stackedPopups);
    
    $(dial).dialog("destroy");
    $(dial).remove();
    creme.utils.stackedPopups.pop();//Remove dial from opened dialog array
//    console.log("creme.utils.stackedPopups post pop:"+creme.utils.stackedPopups);
    if(beforeReloadCb != undefined && $.isFunction(beforeReloadCb))
    {
        beforeReloadCb();
    }
    // add by Jonathan 20/05/2010 in order to have a different callback url for inner popup if needs
    if(callback_url != undefined)
    {
        document.location = callback_url
    }
    else
    {
        if(reload) creme.utils.reloadDialog(creme.utils.stackedPopups[creme.utils.stackedPopups.length-1] || window);//Get the dial's parent dialog or window
    }
//    console.log("Etat de la stack apres le reload:"+creme.utils.stackedPopups);
}

creme.utils.reloadDialog = function(dial){
//    console.log("creme.utils.reloadDialog("+dial+")");
    //if(dial==window) return;//reload(window);
    if(dial==window){
        reload(window);
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

creme.utils.sleep = function(fn, time){
    var time = time || 3000;
    setTimeout(fn, time);
}

creme.utils.appendInUrl = function(url, strToAppend){

    var index_get = url.indexOf('?');
    var get = "", anchor = "";
    if(index_get > -1)
    {
        get = url.substring(index_get, url.length);
        url = url.substring(0, index_get);
    }
    var index_anchor = url.indexOf('#');
    if(index_anchor > -1)
    {
        anchor = url.substring(index_anchor, url.length);
        url = url.substring(0, index_anchor);
    }
    if(strToAppend.indexOf('?') > -1){
        url += strToAppend+get.replace('?','&')+anchor;
    }
    else if(strToAppend.indexOf('&') > -1){
        url += get+strToAppend+anchor;
    }
    else url += strToAppend+get+anchor;
    return url;
}

creme.utils.ajaxDelete = function(url, _data, ajax_params, msg)
{
    creme.utils.showDialog(msg || "Êtes-vous sûr ?",
    {
        buttons: {
            "Ok": function() {
                    var defOpts = jQuery.extend({
                        url : url,
                        data : _data,
                        beforeSend : function(req){
                            creme.utils.loading('loading', false);
                        },
                        success : function(data, status, req){
                            creme.utils.showDialog("Suppression effectuée");
                        },
                        error : function(req, status, error){
                            creme.utils.showDialog("Erreur");
                        },
                        complete : function(request, textStatus){
                            creme.utils.loading('loading', true);
                        },
                        sync : false,
                        type:"POST"
                    }, ajax_params);

                    $.ajax(defOpts);
                    //creme.ajax.json.send(url, defOpts.data, defOpts.success_cb, defOpts.error_cb, defOpts.sync,defOpts.method,defOpts.parameters);
                    $(this).dialog("destroy");
                    $(this).remove();
            },
            "Annuler": function() {$(this).dialog("destroy");$(this).remove();}
        }
    });
}

creme.utils.innerPopupNReload = function(url, reload_url)
{
    creme.utils.showInnerPopup(url,
                              {
                                  beforeClose: function(event, ui, dial) {
                                                    creme.utils.loadBlock(reload_url);
                                                }
                              });
}

creme.utils.handleResearch = function(url, target_node_id, scope)
{
    var _data = {};
    $(scope.targets).each(function(){
       _data[this] = $('[name='+this+']', scope.from).val();
    });
    
    $.ajax({
        url:url,
        type: 'POST',
        data:_data,
        dataType:'html',
        success: function(data, status, req){
            $('#'+target_node_id).html(data);
        },
        error:function(req, status, errorThrown){
        }
    });
}