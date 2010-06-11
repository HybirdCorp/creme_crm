/*
 * File : lv_m2m_widget
 * Author : rbeck
 * Date : $23 nov. 2009 12:02:59$
 */

var lv_widget = {};

lv_widget.init_widget = function(id, q_filter, extra_attrs)
{
    var input = $('#'+id);
    input.hide();
    var td = input.parent();
    var $div = $('<div></div>');
    
    for(var i in extra_attrs)
    {
        var attr = extra_attrs[i];
        if(attr.name && attr.value && attr.name!='id')
            $div.attr(attr.name, attr.value);
    }
    
    td.append(
        $div
        .attr('id', id+'_div')
        .text(
            'Sélectionner '+$('label[for='+id+']').text()
        )
        .append(
            $('<img src="/site_media/images/add_16.png" alt="Ajouter" title="Ajouter"/>')
            .bind('click',
                  {'input' : input, 'input_id' : id, 'lv_widget':lv_widget},
                  function(e){
                        var options = {
                            'send_button': function(dialog){
                                                    var lv = $('form[name="list_view_form"]');
                                                    var ids = lv.list_view("getSelectedEntitiesAsArray");
                                                    if(ids == "" || lv.list_view("countEntities") == 0)
                                                    {
                                                        creme.utils.showDialog("Veuillez sélectioner au moins un enregistrement !", {'title':'Erreur'});
                                                        return;
                                                    }

                                                    if(lv.list_view('option','o2m') && lv.list_view("countEntities") > 1)
                                                    {
                                                        creme.utils.showDialog("Veuillez sélectioner un seul enregistrement !", {'title':'Erreur'});
                                                        return;
                                                    }
                                                    lv_widget.handleSelection(ids, e.data.input_id);
                                                    creme.utils.closeDialog(dialog,false);
                                          },
                          'send_button_label':"Valider la selection"
                        }
//                        var params='menubar=no, status=no, scrollbars=yes, height=800';
                        //openWindow('/creme_core/lv_popup/'+e.data.input.attr('ct_id')+'/'+e.data.input.attr('o2m')+'?js_handler=window.opener.lv_widget.handleSelection&js_arguments=ids,"'+e.data.input_id+'"&q_filter='+q_filter, 'select_multiple_entity', params);
                        var dialog_id = creme.utils.showInnerPopup('/creme_core/lv_popup/'+e.data.input.attr('ct_id')+'/'+e.data.input.attr('o2m')+'?q_filter='+q_filter, options);



                  }
            )
        )
    );      
}

lv_widget.handleSelection = function(ids, targetInputId)
{
    if(ids)
    {
        var $targetInput = $('#'+targetInputId);
        var $targetDiv = $('#'+targetInputId+'_div');
//        $targetDiv.append($('<div></div>').attr('name','container'));
//        var $targetDivContainer = $targetDiv.find('[name=container]');

        var current_language = i18n.get_current_language();
        var o2m = Boolean(parseInt($targetInput.attr('o2m')));

        if(o2m)
        {
            //ids = [ids];
            $targetInput.val('');
        }
        
        
        $targetInput.val($targetInput.val()+ids.join(',')+',');

        for(var i in ids)
        {
            var id = ids[i];
            if(id && id !="")
                $.ajax({
                            type: "GET",
                            url: '/creme_core/entity/get_repr/'+id,
                            dataType: "text",
                            async : false,
                            success: function(data, status){
                                if(o2m)
                                {
                                    $targetDiv.children('div').empty();
//                                    $targetDivContainer.empty();
                                }
                                $targetDiv.append(
                                    $('<div></div>')
                                        .html(data)
                                        .append(
                                            $('<input type="hidden"/>').val(id)
                                        )
                                        .append(
                                            $('<img src="/site_media/images/delete_22.png" alt="'+current_language.DELETE+'" title="'+current_language.DELETE+'"/>')
                                            .attr('onclick', 'lv_widget.delete_a_value(this, "'+targetInputId+'")')
                                        )
                                );
                            },
                            error: function(request, status, error){}
                });
        }

        eval("var selection_cb="+$targetInput.attr('selection_cb'));
        eval("var selection_cb_args="+$targetInput.attr('selection_cb_args'));
        if(selection_cb && $.isFunction(selection_cb))
        {
            selection_cb(ids, targetInputId, selection_cb_args);
        }
        /*if($targetInput.attr('selection_cb') && $.isFunction($targetInput.attr('selection_cb')))
        {
            $targetInput.attr('selection_cb')(ids, targetInputId, $targetInput.attr('selection_cb_args'));
        }*/
        $targetInput.change();
    }
}

lv_widget.delete_a_value = function (img, targetInputId)
{
    var id = $(img).parent().find('input[type="hidden"]').val();
    $('#'+targetInputId).val($('#'+targetInputId).val().replace(id+',', ''));
    $(img).parent().empty().remove();
}