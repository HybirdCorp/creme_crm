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

//TODO: add 'namespace' like creme.campaign....

function loading(is_loaded) {
    creme.utils.loading('loading', is_loaded, {});
}

function disabledUpAndDown() {
    document.getElementById('up').disabled = 'disabled';
    document.getElementById('down').disabled = 'disabled';
}

function loadColumn(except_tab) {
    document.getElementById('trgenerate').style.display = 'none';
    document.getElementById('trcustomops').style.display = 'none';

    if (except_tab == undefined) {
        $('#recapcolumn > option').remove();
    }

    var ct_id = document.getElementById('ct').value;

    $.ajax({
        url: "/reports/ajax/load_columns",
        async : false,
        type: "POST",
        data: ({'ct': ct_id, 'except_tab' : except_tab}),
        dataType: "json",
        cache : false,
        beforeSend: loading(false),
        success: function(data) {
                var options = '<option value="Toutes">Toutes</option>';
                for (var i = 0; i < data.length; i++) {
                    options += '<option value="' + data[i] + '">' + data[i] + '</option>';
                }
                $("select#column").html(options);

                document.getElementById("trcolumn").style.display = 'table-row';
                document.getElementById("preview_div").style.display = 'none';

                disabledUpAndDown(); //TODO: used only once ......

                document.getElementById("trfilter").style.display = 'none';
        },
        complete: loading(true)
    });
}

function loadFilters(select) {
    var ct_id = $(select).val();
    $.ajax({
        url: "/reports/ajax/load_filters",
        async : false,
        type: "POST",
        data: ({'ct' : ct_id}),
        dataType: "json",
        cache : false,
        beforeSend: loading(false),
        success: function(filters) {
                var selector = $("select#filter");
                var filter;

                selector.empty();
                selector.append($('<option/>').attr('value', '0').text('Tous'));

                for(var i = 0; i < filters.length; ++i) {
                    filter = filters[i];
                    selector.append($('<option/>').attr('value', filter.id).text(filter.name));
                }
        },
        complete: loading(true)
    });
}

function loadEntities() {
    var select_ct = document.getElementById('ct');
    var select_filter = document.getElementById('filter');
    var column_recap = document.getElementById('recapcolumn');
    var selected = new Array();

    for (var i = 0; i < column_recap.options.length; i++) {
        selected.push(column_recap.options[i].value);
    }

    if (select_filter != undefined) {
        $.ajax({
            url: "/reports/ajax/load_preview",
            async : false,
            type: "POST",
            data: ({'filter' : select_filter.value, 'ct' : select_ct.value, 'column_tab' : selected}),
            dataType: "json",
            cache : false,
            beforeSend: loading(false),
            success: function(data) {
                    var preview = document.getElementById("preview_div")
                    preview.innerHTML = data;
                    preview.style.display = 'block';

                    loadAcceptedColumns($('#ops'));
            },
            complete: loading(true)
        });
    }
}

function del(select_id, all) {
    if (all == true) {
        $('#' + select_id + " > option").remove();
    } else {
        $('#' + select_id + " > option:selected").remove();
    }
}

function delItem() {
    var select_to_get_except = document.getElementById("recapcolumn");
    var except_tab = new Array();

    for (var i = 0; i < select_to_get_except.options.length; i++) {
        if (!select_to_get_except.options[i].selected) {
            except_tab.push(select_to_get_except.options[i].value);
        }
    }

    var j = 0;
    for (var i = 0; i < select_to_get_except.options.length; i++) {
        if (select_to_get_except.options[i].selected == true) {
            j = j + 1;
        }
    }

    if (j > 0) { //TODO: un simple booleen suffit non ??
        loadColumn(except_tab);

        del("recapcolumn", false);

        loadEntities();

        document.getElementById('trfilter').style.display = 'table-row';
        document.getElementById('trgenerate').style.display = 'table-row';
        document.getElementById('trcustomops').style.display = 'table-row';
    }
}

function addItem() {
    var select_column = document.getElementById("column");
    var is_all_selected = false;

    for (var i = 0; i < select_column.options.length; i++) {
        if ((select_column.options[i].selected) && (select_column.options[i].value == "Toutes")) { //BEURK !!!!!!!!!!
            is_all_selected = true;
        }
    }

    if (is_all_selected) {
        for (var i = 0; i < select_column.options.length; i++) {
            if (select_column.options[i].value == "Toutes") { //BEURK !!!!!!!!!!
                continue;
            }
            var option = '<option value="' + select_column.options[i].value + '">' + select_column.options[i].value + "</option>";
            $("#recapcolumn").append($(option));
        }
        del("column", true)
    } else {
        var selected = new Array();

        for (var i = 0; i < select_column.options.length; i++) {
            if (select_column.options[i].selected) {
                selected.push(select_column.options[i].value);
            }
        }

        for (var i = 0; i < selected.length; i++) {
            $("#recapcolumn").append($('<option value="' + selected[i] + '">' + selected[i] + '</option>'));
        }

        // on delete les selected values de la column parent
        del("column", false);
    }

    // Render of step 3
    document.getElementById("trfilter").style.display = 'table-row';
    document.getElementById('trgenerate').style.display = 'table-row';
    document.getElementById('trcustomops').style.display = 'table-row';

    // Reload preview
    loadEntities();
}

function addFilter() {
    var ct_id = $('#ct').val();
    var url = "/creme_core/filter/add/" + ct_id;
    $(window.document).attr('location', url);
}

function editFilter() {
    var filter_id = $('#filter').val()
    var ct_id = $('#ct').val();
    var url = "/creme_core/filter/edit/" + ct_id + "/" + filter_id;
    $(window.document).attr('location', url);
}

function delFilter() {
    var filter_id = $('#filter').val()
    var url = "/creme_core/filter/delete/" + filter_id;
    $(window.document).attr('location', url);
}

function cleanAll() {
    $('#recapcolumn'+" > option").remove();
    loadColumn();
    loadEntities();
}

function upItem() {
    var recapcolumn = document.getElementById('recapcolumn');

    var obj_to_up = $('#recapcolumn > option:selected');

    if (obj_to_up.val() == recapcolumn.options[0].value) {
        return null;
    }

    var options = new Array();

    for (var i = 0; i < recapcolumn.options.length; i++) {
        if (recapcolumn.options[i].value == obj_to_up.val()) {
            var obj = recapcolumn.options[i - 1];
            options.pop()
            options.push(recapcolumn.options[i]);
            options.push(obj);
        } else {
            options.push(recapcolumn.options[i]);
        }
    }

    $('#recapcolumn > option').remove();
    for (var i = 0; i < options.length; i++) {
        $('#recapcolumn').append($(options[i]))
    }
    loadEntities();
    checkUpandDown();
}

function downItem() {
    var recapcolumn = document.getElementById('recapcolumn');

    var obj_to_down = $('#recapcolumn > option:selected');

    if (obj_to_down.val() == recapcolumn.options[recapcolumn.options.length - 1].value) {
        return null;
    }

    var options = new Array();
    var operation_done = false;

    for (var i = 0; i < recapcolumn.options.length; i++) {
        if ((recapcolumn.options[i].value == obj_to_down.val()) && operation_done == false) {
            options.push(recapcolumn.options[i+1]);
            options.push(recapcolumn.options[i]);
            operation_done = true
        } else {
            // si not contains
            var already_exists = false;

            for (var j = 0; j < options.length; j++) {
                if (options[j] == recapcolumn.options[i]) {
                    already_exists = true;
                    //TODO: break ????
                }
            }

            if (!already_exists) {
                options.push(recapcolumn.options[i]);
            }
        }
    }

    $('#recapcolumn > option').remove();
    for (var i = 0; i < options.length; i++) {
        $('#recapcolumn').append($(options[i]))
    }

    loadEntities();
    checkUpandDown();
}

function checkUpandDown() {
    var button_up = document.getElementById('up');
    var button_down = document.getElementById('down');

    button_up.disabled = '';
    button_down.disabled = '';

    var select_opt = document.getElementById("recapcolumn").options;
    var selected = new Array();

    for (var i = 0; i < select_opt.length; i++) {
        if (select_opt[i].selected) {
            selected.push(select_opt[i].value);
        }
    }

    if (selected.length == 1) {
        if (selected[0] == select_opt[select_opt.length - 1].value) {
            button_down.disabled = 'disabled';
        }
        if (selected[0] == select_opt[0].value) {
            button_up.disabled = 'disabled';
        }
    }
}

function loadAcceptedColumns(select) {
    var select_opt = document.getElementById("recapcolumn").options;
    var fields_list = new Array();

    for (var i = 0; i < select_opt.length; i++) {
        fields_list.push(select_opt[i].value);
    }

    $.ajax({
        url: "/reports/ajax/load_operable_columns",
        async : false,
        type: "POST",
        data: ({'op' : $(select).val(), 'fields_list': fields_list, 'ct': $('#ct').val()}),
        dataType: "json",
        cache : false,
        beforeSend: function(request) {
            $('#add_operation').attr('disabled', 'disabled');
            creme.utils.loading('loading', false, {});
        },
        success: function(data) {
            var options = '';

            if (data.length > 0) {
                $('#add_operation').attr('disabled', '');
            }

            for (var i = 0; i < data.length; i++) {
                options += '<option value="' + data[i] + '">' + data[i] + '</option>';
            }
            $("#columnscustom").html(options);
        },
        complete : function(request, txtStatus) {
            creme.utils.loading('loading', true, {});
        }
    });
}

function addOperation() {
    var hidden = $('#hidden');
    var operation = $('#ops');
    var operation_list = $('#operations_list');
    var op_value = operation.value;
    var displaydiv = $('#appercuop');
    //var columnscustom = $("#columnscustom");
    var selected = '';
    $("#columnscustom option:selected").each(function(ind) {
        var old_val = operation_list.val();
        if (old_val != '')
            var new_val = old_val + '|' + operation.val() + ',' + $(this).val();
        else
            var new_val = operation.val() + ',' + $(this).val();
        hidden.html(new_val);
        displaydiv.html(new_val);
        operation_list.val(new_val);
    });
}

function prepareSubmit(format) {
    var myform = document.getElementById('myform');
    myform.action = '/reports/ajax/generate' + format;
    var hidden = document.getElementById('fields_list');
//     var operations = document.getElementById('operations_list')
//     var divhidden = document.getElementById('hidden');
    var fields_list = '';

    var recap_select = document.getElementById('recapcolumn');
    for (var i = 0; i < recap_select.options.length; i++) {
        if (i == 0) { //TODO: sortir ce teste de la boucle....
            fields_list = recap_select.options[i].value;
        } else {
            fields_list += ',' + recap_select.options[i].value;
        }
    }
    //operations.value = divhidden.innerHTML;
    hidden.value = fields_list;
    myform.submit();
}

// same as prepareSubmit() without generation format parameter. just save.
function saveReport() 
{
	var myform = document.getElementById('myform');
    myform.action = '/reports/ajax/save';  // be carefull, changes the form action url ! could cause some side effects.
    var hidden = document.getElementById('fields_list');
//     var operations = document.getElementById('operations_list')
//     var divhidden = document.getElementById('hidden');
    var fields_list = '';

    var recap_select = document.getElementById('recapcolumn');
    for (var i = 0; i < recap_select.options.length; i++) {
        if (i == 0) { //TODO: sortir ce teste de la boucle....
            fields_list = recap_select.options[i].value;
        } else {
            fields_list += ',' + recap_select.options[i].value;
        }
    }
    //operations.value = divhidden.innerHTML;
    hidden.value = fields_list;
    myform.submit();
}

