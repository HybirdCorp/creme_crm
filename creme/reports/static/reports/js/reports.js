/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2014  Hybird

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

if (!creme.reports) creme.reports = {};


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
            $target_select.append($('<option value="' + d[0] + '">' + d[1] + '</option>'));
        }
    };

    var error_cb = function(req, textStatus, err) {
        // WTF: 'error_option' not used ?!
        if (!params.error_option) {
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
        'always_option': $('<option value="">' + gettext("No selected view") + '</option>')
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
}

creme.reports.changeOrder = function(field_id, direction, block_url) {
    return creme.reports.doAjaxAction('/reports/report/field/change_order', {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'direction': direction
                                      });
}

creme.reports.setSelected = function(checkbox, field_id, block_url) {
    return creme.reports.doAjaxAction('/reports/report/field/set_selected', {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'checked': $(checkbox).is(':checked') ? 1 : 0
                                      });
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


creme.reports.exportReport = function(link, report_id, title) {
    var filterform_url = '/reports/export/filter/%d'.format(report_id)

    // The export view uses the 'callback_url' feature of inner_popup (maybe only used here).
    // Emulate it for this case.
    // TODO : filterform should be used as select and redirection url build in js.
    creme.dialogs.form(filterform_url, {'title': title || ''})
                 .on('frame-update', function(event, frame) {
                      new creme.reports.PreviewController(report_id).bind(frame.delegate());
                  })
                 .onFormSuccess(function(event, data, statusText, dataType) {
                       var matches = data.match(/^<div class="in-popup" closing="true" redirect="(.*)">/)

                       if (matches && matches.length > 1) {
                           creme.utils.goTo(matches[1]);
                       }
                  })
                 .open({width:1024});
}

creme.reports.openGraphEdition = function(graph_id, reload_uri)
{
    creme.blocks.form('/reports/graph/edit/%s'.format(graph_id), {blockReloadUrl:reload_uri})
                .onFormSuccess(function() {
                     $('#graph-%s .ui-creme-plotselector'.format(graph_id)).creme().widget().resetBackend();
                 }).open();
}


creme.reports.PreviewController = creme.component.Component.sub({
    _init_: function(report)
    {
        this._redirectUrl = '/reports/export/preview/' + report + '?%s';
        this._downloadUrl = '/reports/export/' + report + '?%s';

        this._listeners = {
            update:   $.proxy(this._updateHeader, this),
            redirect: $.proxy(this.redirect, this),
            download: $.proxy(this.download, this)
        }
    },

    bind: function(element)
    {
        if (this._header !== undefined)
            throw 'creme.reports.PreviewController is already bound.';

        var listeners = this._listeners;
        var header = this._header = $('.report-preview-header', element);

        $('select[name="date_field"]',    header).change(listeners.update);
        $('select[name="date_filter_0"]', header).change(listeners.update);

        $('button[name="generate"]', header).click(listeners.redirect);
        $('button[name="download"]', header).click(listeners.download);

        this._updateHeader();
        return this;
    },

    unbind: function(element)
    {
        var listeners = this._listeners;
        var header = this._header;

        if (header !== undefined)
        {
            $('select[name="date_field"]',    header).unbind('change', listeners.update);
            $('select[name="date_filter_0"]', header).unbind('change', listeners.update);

            $('button[name="generate"]', header).unbind('click', listeners.redirect);
            $('button[name="download"]', header).unbind('click', listeners.download);
        }

        this._header = undefined;
        return this;
    },

    _updateHeader: function()
    {
        var header = this._header;

        var has_datefield = !Object.isEmpty($('[name="date_field"]', header).val());
        var has_customdaterange = Object.isEmpty($('[name="date_filter_0"]', header).val());

        $('.date-filter', header).toggle(has_datefield);
        $('[name="date_filter_1"], [name="date_filter_2"]', header).each(function() {
            $(this).parents('td:first').toggle(has_customdaterange);
        });

        if (!has_customdaterange) {
            $('[name="date_filter_1"], [name="date_filter_2"]', header).val('');
        }

        if (!has_datefield) {
            $('[name^="date_filter_"]', header).val('');
        }
    },

    redirect: function() {
        creme.utils.goTo(this._redirectUrl.format($('form', this._header).serialize()));
    },

    download: function() {
        creme.utils.goTo(this._downloadUrl.format($('form', this._header).serialize()));
    }
});
