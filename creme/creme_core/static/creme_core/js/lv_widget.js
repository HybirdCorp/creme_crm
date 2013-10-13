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

// if(!creme.relations) creme.relations = {}  ???
creme.lv_widget = {};

creme.lv_widget.init_widget = function(id, q_filter, extra_attrs) {
    var input = $('#' + id);
    input.hide();
    var td = input.parent();
    var $div = $('<div></div>');

    for (var i in extra_attrs) {
        var attr = extra_attrs[i];

        if (attr.name && attr.value && attr.name!='id')
            $div.attr(attr.name, attr.value);
    }

    td.append(
        $div
        .attr('id', id + '_div')
        .text(gettext("Select") + ' : ' + $('label[for=' + id + ']').text())
        .addClass('defaultcur')
        .append(
            $('<img />').attr('src', creme_media_url("images/add_16.png")).attr('alt', gettext("Add")).attr('title', gettext("Add"))
            .bind('click',
                  {input: input, input_id: id, lv_widget: creme.lv_widget},
                  function(e) {
                        var options = {
                            send_button: function(dialog) {
                                var lv = $('form[name="list_view_form"]');
                                var ids = lv.list_view("getSelectedEntitiesAsArray");
                                if (ids == "" || lv.list_view("countEntities") == 0) {
                                    creme.utils.showDialog(gettext("Please select at least one entity."),
                                                            {'title': gettext("Error")});
                                    return;
                                }

                                if (lv.list_view('option', 'o2m') && lv.list_view("countEntities") > 1) {
                                    creme.utils.showDialog(gettext("Please select only one entity."),
                                                            {'title': gettext("Error")});
                                    return;
                                }
                                creme.lv_widget.handleSelection(ids, e.data.input_id);
                                creme.utils.closeDialog(dialog, false);
                            },
                            send_button_label: gettext("Validate the selection")
                        }
//                        var params='menubar=no, status=no, scrollbars=yes, height=800';
                        var dialog_id = creme.utils.showInnerPopup('/creme_core/lv_popup/' + e.data.input.attr('ct_id') + '/' + e.data.input.attr('o2m') + '?q_filter=' + q_filter, options);
                  }
            )
            .addClass('pointer')
        )
    );
}

creme.lv_widget.handleSelection = function(ids, targetInputId) {
    if(ids) { //TODO: use a guard
        var $targetInput = $('#' + targetInputId);
        var $targetDiv = $('#' + targetInputId + '_div');

        var o2m = Boolean(parseInt($targetInput.attr('o2m')));

        if (o2m) {
            ids = [ids];
            $targetInput.val('');
        }

        var currentIds = $targetInput.val().split(',');

        ids = $.grep(ids, function(n, i) {
            return !($.inArray(n, currentIds) > -1);
        });

        var comma_sep_ids = ids.join(',');
        $targetInput.val(comma_sep_ids+ ',' + currentIds.join(','));
        $targetInput.val($targetInput.val().replace(',,',','));

        if (ids.length > 0) {
            $.ajax({
                    type: "GET",
                    url: '/creme_core/entity/get_repr/' + comma_sep_ids,
                    dataType: "json",
                    async : false,
                    success: function(data, status) {
                        if(o2m) {
                            $targetDiv.children('div').empty();
                        }

                        for(var idx in data) {
                            var d = data[idx];
                            $targetDiv.append(
                                $('<div></div>')
                                    .append($('<span></span>').html(d.text).append($('<input type="hidden"/>').val(d.id)))
                                    .append($('<img />').attr('src', creme_media_url("images/delete_22.png"))
                                                        .attr('alt', gettext("Delete"))
                                                        .attr('title', gettext("Delete"))
                                                        .css('cursor', 'pointer')
                                                        .attr('onclick', 'creme.lv_widget.delete_a_value(this, "' + targetInputId + '")')
                                    )
                            );
                        }

                        var widths = []
                        $targetDiv.children('div').find('span').each(function() {
                            widths.push($(this).width());
                        });

                        if (widths.length > 1) {
                            var maxW = Math.max.apply(Math, widths);

                            $targetDiv.children('div').find('img').each(function(i) {
                                $(this).css('padding-left', maxW-widths[i]);
                            });
                        }

                    },
                    error: function(request, status, error) {}
            });
        }

        eval("var selection_cb=" + $targetInput.attr('selection_cb')); //WTF ??
        eval("var selection_cb_args=" + $targetInput.attr('selection_cb_args'));  //WTF ??
        if (selection_cb && $.isFunction(selection_cb)) {
            selection_cb(ids, targetInputId, selection_cb_args);
        }

        $targetInput.change();
    }
}

//TODO: rename
creme.lv_widget.delete_a_value = function (img, targetInputId) {
    //TODO: factorise "$(img).parent()", "$('#' + targetInputId)" ??
    var id = $(img).parent().find('input[type="hidden"]').val();
    $('#' + targetInputId).val($('#' + targetInputId).val().replace(id + ',', ''));
    $(img).parent().empty().remove();
}
