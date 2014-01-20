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

/*
 * Requires : creme, jQuery, creme.utils, creme.ajax
 */

if(!creme.reports) creme.reports = {};

//TODO: in creme_core ??
creme.reports.loading_options = {
    beforeSend : function(request) {
          creme.utils.loading('loading', false, {});
      },
    complete: function (XMLHttpRequest, textStatus) {
          creme.utils.loading('loading', true, {});
      }
};

creme.reports.load = function(options) {
    if(!options || options == undefined) return;

    var ct_id = $(options.ct).val();
//     if(!ct_id || ct_id =="") {
//         $(options.show_after_ct).hide();
//         return;
//     }

    var $hf = $(options.hf);
    this.loadHeaderFilters(ct_id, $hf);

    var $filter = $(options.filter);
    this.loadFilters(ct_id, $filter);

//     this.loadRegularFields(ct_id, options);
//     this.loadRelatedFields(ct_id, options);
//     this.loadCf(ct_id, options);
//     this.loadRelations(ct_id,  options);
//     this.loadFunctions(ct_id,  options);
//     this.loadAggregates(ct_id, options);
// 
//     $(options.show_after_ct).show();
}

//TODO: Could use creme.forms.Select.optionsFromData & creme.forms.Select.fill with a hack for default/error options?
creme.reports.__loadFilters = function(url, ct_id, $target_select, parameters) {
    if($target_select.size() != 1) return;

    var params = $.extend({
        'err_label' : gettext("None available"),
        'always_option': null,//Always the 1st option in non-empty success cases
        'empty_option' : null,
        'error_option' : null
    }, parameters);

    var $def_option = $('<option value="">' + params.err_label + '</option>');

    var success_cb = function(data, textStatus, req) {
        $target_select.empty();

        //TODO: factorise 'data.length == 0'
        if (data.length == 0 && !params.empty_option) {
            $target_select.append($def_option);
        }
        if (data.length == 0 && params.empty_option) {
            $target_select.append(params.empty_option);
        }
        if (data.length > 0 && params.always_option) {
            $target_select.append(params.always_option);
        }

        for (var i in data) {
            var d = data[i];
//             $target_select.append($('<option value="'+d.pk+'">'+d.fields.name+'</option>'));
            $target_select.append($('<option value="' + d[0] + '">' + d[1] + '</option>'));
//             $target_select.append($('<option></option>').attr('value', d[0]).append(d[1]));
        }
    };

    var error_cb = function(req, textStatus, err) {
        if (!params.err_option) {
            $target_select.empty().append($def_option);
        } else {
            $target_select.empty().append(params.empty_option);
        }
    };

    creme.ajax.json.get(url, {}, success_cb, error_cb, false, this.loading_options);
}

creme.reports.loadHeaderFilters = function(ct_id, $target_select) {
    var url = '/creme_core/header_filter/get_for_ctype/' + ct_id;
    var params = {
//         'always_option': $('<option value="">' + gettext("No selected view") + '</option>')
    };
    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}


creme.reports.loadFilters = function(ct_id, $target_select) {
    var url = '/creme_core/entity_filter/get_for_ctype/' + ct_id;
    var $all_opt = $('<option value="">' + gettext("All") + '</option>');

    var params = {
        'empty_option' : $all_opt,
        'always_option': $all_opt,
        'error_option' : $all_opt
    };

    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}

/*
//todo: refactor when OrderedMultiSelect can be properly reload
creme.reports.__loadOrderedMultiSelect = function(url, pdata, table_id, input_name) {
    var $columns_table = $('#' + table_id);

    if($columns_table.size() !=1) return;

    var $tbody = $columns_table.find('tbody');

    var success_cb = function(data, textStatus, req){
        $tbody.empty();
        $columns_table.parent('.dcms_div').children().not($columns_table).remove();

        for(var i in data) {
            var d = data[i];
            var val = d[0];
            var txt = d[1];

            var $tr = $('<tr />').attr('name', 'oms_row_'+i);

            var $td1 = $('<td><input class="oms_check" type="checkbox" name="'+input_name+'_check_'+i+'" /></td>');
            var $td2 = $('<td class="oms_value">'+txt+'<input type="hidden" value="'+val+'" name="'+input_name+'_value_'+i+'"/></td>');
            var $td3 = $('<td><input class="oms_order" type="text" name="'+input_name+'_order_'+i+'" value=""/></td>');

            $tbody.append($tr.append($td1).append($td2).append($td3));
        }
        creme.forms.toOrderedMultiSelect(table_id);
    };

    var error_cb = function(req, textStatus, err){
        $tbody.empty();
        $columns_table.parent('.dcms_div').children().not($columns_table).remove();
    };

    creme.ajax.json.post(url, pdata, success_cb, error_cb, false, this.loading_options);
}

creme.reports.loadRegularFields = function(ct_id, options) {
    creme.reports.__loadOrderedMultiSelect('/creme_core/entity/get_fields',
                                           {'ct_id': ct_id},
                                           options.regular_fields.table_id,
                                           options.regular_fields.name
                                          );
}

creme.reports.loadRelatedFields = function(ct_id, options) {
    creme.reports.__loadOrderedMultiSelect('/reports/get_related_fields',
                                           {'ct_id': ct_id},
                                           options.related_fields.table_id,
                                           options.related_fields.name);
}

creme.reports.loadCf = function(ct_id, options) {
    creme.reports.__loadOrderedMultiSelect('/creme_core/entity/get_custom_fields',
                                       {'ct_id': ct_id},
                                       options.cf.table_id,
                                       options.cf.name);
}

creme.reports.loadRelations = function(ct_id, options) {
    creme.reports.__loadOrderedMultiSelect('/reports/get_predicates_choices_4_ct',
                                       {'ct_id': ct_id},
                                       options.relations.table_id,
                                       options.relations.name);
}

creme.reports.loadFunctions = function(ct_id, options) {
    creme.reports.__loadOrderedMultiSelect('/creme_core/entity/get_function_fields',
                                       {'ct_id': ct_id},
                                       options.functions.table_id,
                                       options.functions.name);
}

creme.reports.loadAggregates = function(ct_id, options) {
    for(var i = 0; i < options.aggregates.length; i++) {
        var current_aggregate = options.aggregates[i];
        creme.reports.__loadOrderedMultiSelect('/reports/get_aggregate_fields',
                                           {
                                            'aggregate_name': current_aggregate.name,
                                            'ct_id': ct_id
                                           },
                                           current_aggregate.target_node,
                                           current_aggregate.input_name);
    }
}
*/

/*
creme.reports.getContentTypeForPredicate = function(predicate, success_cb, error_cb) {
    creme.ajax.json.get('/creme_core/relation/type/' + predicate + '/content_types/json',
            {
                fields:['id', 'unicode']
                // sort:'name' deprecated field
            }, success_cb, error_cb);
}

creme.reports.link_relation_report = function(report_id, field_id, predicate, block_url) {
    var success_cb = function(data, textStatus, req) {
        var $select = $('<select />');
        creme.forms.Select.fill($select, [["", gettext("Select a type")]].concat(data), "");

        var buttons = {};
        buttons[gettext("Ok")] = function() {
                if($select.val() == "") {
                    creme.dialogs.warning(gettext("Please select a type."));
                    return;
                }

                creme.blocks.form('/reports/report/'+report_id+'/field/'+field_id+'/link_relation_report/'+$select.val(), {blockReloadUrl:block_url}).open();

                $(this).dialog("close");
            }

        creme.utils.showDialog($select, {buttons: buttons});
    }

    var error_cb = function(req, textStatus, err) {

    }

    creme.reports.getContentTypeForPredicate(predicate, success_cb, error_cb);
}
*/

creme.reports.AJAX_BACKEND = new creme.ajax.CacheBackend(new creme.ajax.Backend(), {
                                                             condition: new creme.ajax.CacheBackendTimeout(120 * 1000),
                                                             dataType: 'json'
                                                         });

creme.reports.doAjaxAction = function(url, options, data) {
    var options = options || {};
    var query = creme.reports.AJAX_BACKEND.query();
    var reload_cb = options.blockReloadUrl ? function() {creme.blocks.reload(options.blockReloadUrl);} : function() {};

    query.url(url)
         .onDone(reload_cb)
         .onFail(function(event, req) {
             creme.dialogs.warning(req.responseText || gettext("Error"))
                          .onClose(reload_cb)
                          .open();
          })
         .post(data);

    return query;
}

creme.reports.unlink_report = function(field_id, block_url) {
    creme.reports.doAjaxAction('/reports/report/field/unlink_report', {
                                   blockReloadUrl: block_url
                               }, {
                                   'field_id': field_id
                               });

/*
    var success_cb = function(data, textStatus, req) {
        if (block_url && block_url != undefined) {
            creme.blocks.reload(block_url);
        }
    };

    var error_cb = function(req, textStatus, err) {

    };

    creme.ajax.json.post('/reports/report/field/unlink_report',
                         {'field_id': field_id}, success_cb, success_cb,
                         false, this.loading_options
                        );
*/
}

/*
creme.reports.link_report = function(field_id, block_url) {
    var url = '/reports/report/field/%s/link_report'.format(field_id);
    return creme.blocks.form(url, {blockReloadUrl:block_url}).open();
}

creme.reports.link_related_report = function(field_id, block_url) {
    var url = '/reports/report/field/%s/link_related_report'.format(field_id);
    return creme.blocks.form(url, {blockReloadUrl:block_url}).open();
}

creme.reports.link_relation_report = function(field, predicate, block_url) {
    var query = creme.reports.AJAX_BACKEND.query();

    query.url('/creme_core/relation/type/%s/content_types/json'.format(predicate))
         .onDone(function(event, data) {
              var choices = data ? data.map(function(item) {return {value:item[0], label:item[1]};}) : [];

              creme.dialogs.choice(gettext('Select a type'), {
                                title: gettext('Link relation to report'),
                                choices: choices
                            })
                           .onOk(function(event, type) {
                                if (Object.isEmpty(type)) {
                                    creme.dialogs.warning(gettext("Please select a type."));
                                    return;
                                }

                                var url = '/reports/report/field/%s/link_relation_report/%s'.format(field, type);

                                creme.blocks.form(url, {blockReloadUrl:block_url}).open();
                            })
                           .open();
          })
         .get({fields:['id', 'unicode']});

     return query;
}
*/

creme.reports.changeOrder = function(field_id, direction, block_url) {
    return creme.reports.doAjaxAction('/reports/report/field/change_order', {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'direction': direction
                                      });

/*
    var success_cb = function(data, textStatus, req) {
        if(block_url && block_url != undefined) {
            creme.blocks.reload(block_url);
        }
    };

    var error_cb = function(req, textStatus, err) {
        creme.utils.showDialog(req.responseText || gettext("Error"));
        if(block_url && block_url != undefined) {
            creme.blocks.reload(block_url);
        }
    };

    var data = {'report_id': report_id, 'field_id': field_id, 'direction': direction};

    creme.ajax.json.post('/reports/report/field/change_order', data, success_cb, success_cb, false, this.loading_options);
*/
}

creme.reports.setSelected = function(checkbox, field_id, block_url) {
    return creme.reports.doAjaxAction('/reports/report/field/set_selected', {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'checked': $(checkbox).is(':checked') ? 1 : 0
                                      });
/*
    var success_cb = function(data, textStatus, req) {
        if(block_url && block_url != undefined) {
            creme.blocks.reload(block_url);
        }
    };

    var error_cb = function(req, textStatus, err) {
        creme.utils.showDialog(req.responseText || gettext("Error"));
        if(block_url && block_url != undefined) {
            creme.blocks.reload(block_url);
        }
    };

    var data = {'report_id': report_id, 'field_id': field_id, 'checked': +$(checkbox).is(':checked')};

    creme.ajax.json.post('/reports/report/field/set_selected', data, success_cb, success_cb, false, this.loading_options);
*/
};

creme.reports.toggleDisableOthers = function(me, others) {
    var is_checked = me.checked;//More generic with all node types ?
    $.each(others, function(i, n) {
        $(n).attr('disabled', is_checked);
    });
};

creme.utils.converters.register('creme.graphael.BargraphData', 'jqplotData', function(data) {
    var ticks = data['x'] || [];
    var values = data['y'] || [];
    var jqplotData = []

    var clean_float = function(value) {
        var res = parseFloat(value);
        return isNaN(res) ? 0.0 : res;
    }

    for (var index = 0; index < Math.min(ticks.length, values.length); ++index) {
        var tick = ticks[index];
        var value = values[index];
        var item;

        if (typeof value === 'string') {
            item = [tick, clean_float(value), undefined];
        } else if ($.isArray(value)) {
            item = [tick, clean_float(value[0]), value[1]];
        } else {
            item = [tick, value, undefined];
        }

        jqplotData.push(item);
    }

    return jqplotData.length ? [jqplotData] : [];
});


creme.reports.exportReport = function(link, backends, filterurl) {
    if (backends.length) {
        creme.dialogs.form(filterurl).open({width:800});
    } else {
        creme.dialogs.warning(gettext('No backend found')).open({maxWidth:300, resizable:false});
    }
}

creme.reports.openGraphEdition = function(graph_id, reload_uri)
{
    creme.blocks.form('/reports/graph/edit/%s'.format(graph_id), {blockReloadUrl:reload_uri})
                .onFormSuccess(function() {
                     $('#graph-%s .ui-creme-plotselector'.format(graph_id)).creme().widget().resetBackend();
                 }).open();
}

/*
if(!creme.reports.graphs) creme.reports.graphs = {};

creme.reports.graphs.bind_toggle_graph = function(selectors, show_cb) {
    $.each(selectors, function(idx, obj){
        var $shower    = $(obj.shower);
        var $hider     = $(obj.hider);
        var $wrapper   = $(obj.wrapper);
        var $container = $(obj.container);

        $shower.bind('click', function() {
            var $s = $(obj.shower);
            var $p = $s.parent();
            $p.attr('rowspan', 2);

            $wrapper.show();
            $hider.show();
            $s.hide();

            if(show_cb != undefined && $.isFunction(show_cb)) {
                show_cb(obj);
            }
        });

        $hider.bind('click', function() {
            var $h = $(this);
            var $p = $h.parent();
            //$p.removeAttr('rowspan');//Bug in IE
            $p.attr('rowspan', 1);

            $wrapper.hide();
            $shower.show();
            $h.hide();
        });
    });
};
*/
