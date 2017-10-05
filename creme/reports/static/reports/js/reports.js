/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2017  Hybird

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
 * Requires : creme, jQuery, creme.utils, creme.ajax, creme.dialogs
 */

(function($) {
"use strict";

if (!creme.reports) creme.reports = {};


//creme.reports.load = function(options) {
creme.reports.load = function(options, hfilters_url, efilters_url) {
    if (!options || options == undefined) return;

    var ct_id = $(options.ct).val();
    var $hf = $(options.hf);
//    this.loadHeaderFilters(ct_id, $hf);
    this.loadHeaderFilters(hfilters_url, ct_id, $hf);

    var $filter = $(options.filter);
//    this.loadFilters(ct_id, $filter);
    this.loadEntityFilters(efilters_url, ct_id, $filter);
};

//TODO: Could use creme.forms.Select.optionsFromData & creme.forms.Select.fill with a hack for default/error options?
creme.reports.__loadFilters = function(url, ct_id, $target_select, parameters) {
    if ($target_select.size() != 1) return;

    var params = $.extend({
        'err_label':     gettext("None available"),
        'always_option': null, // Always the 1st option in non-empty success cases
        'empty_option':  null,
        'error_option':  null
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
};

//creme.reports.loadHeaderFilters = function(ct_id, $target_select) {
creme.reports.loadHeaderFilters = function(url, ct_id, $target_select) {
//    var url = '/creme_core/header_filter/get_for_ctype/' + ct_id;
    var url = url + '?' + $.param({ct_id: ct_id});
    var params = {
        'always_option': $('<option value="">' + gettext("No selected view") + '</option>')
    };
    creme.reports.__loadFilters(url, ct_id, $target_select, params);
};

//creme.reports.loadFilters = function(ct_id, $target_select) {
creme.reports.loadEntityFilters = function(url, ct_id, $target_select) {
//    var url = '/creme_core/entity_filter/get_for_ctype/' + ct_id;
    var url = url + '?' + $.param({ct_id: ct_id});
    var $all_opt = $('<option value="">' + gettext("All") + '</option>');
    var params = {
        'empty_option' : $all_opt,
        'always_option': $all_opt,
        'error_option' : $all_opt
    };
    creme.reports.__loadFilters(url, ct_id, $target_select, params);
};


creme.reports.AJAX_BACKEND = new creme.ajax.CacheBackend(new creme.ajax.Backend(), {
                                                             condition: new creme.ajax.CacheBackendTimeout(120 * 1000),
                                                             dataType: 'json'
                                                         });

creme.reports.doAjaxAction = function(url, options, data) {
    console.warn('creme.reports.doAjaxAction() is deprecated ; use bricks & actions instead.');

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
};

//creme.reports.unlink_report = function(field_id, block_url) {
creme.reports.unlink_report = function(url, field_id, block_url) {
//    creme.reports.doAjaxAction('/reports/report/field/unlink_report', {
    console.warn('creme.reports.unlink_report() is deprecated ; use the new bricks action system instead.');

    creme.reports.doAjaxAction(url, {
                                   blockReloadUrl: block_url
                               }, {
                                   'field_id': field_id
                               });
}

//creme.reports.changeOrder = function(field_id, direction, block_url) {
creme.reports.changeOrder = function(url, field_id, direction, block_url) {
//    return creme.reports.doAjaxAction('/reports/report/field/change_order', {
    console.warn('creme.reports.changeOrder() is deprecated ; use the new bricks ordering system instead.');

    return creme.reports.doAjaxAction(url, {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'direction': direction
                                      });
};

//creme.reports.setSelected = function(checkbox, field_id, block_url) {
creme.reports.setSelected = function(url, checkbox, field_id, block_url) {
//    return creme.reports.doAjaxAction('/reports/report/field/set_selected', {
    console.warn('creme.reports.setSelected() is deprecated.');

    return creme.reports.doAjaxAction(url, {
                                          blockReloadUrl: block_url
                                      }, {
                                          'field_id': field_id,
                                          'checked': $(checkbox).is(':checked') ? 1 : 0
                                      });
};

creme.reports.toggleDisableOthers = function(me, others) {
    var is_checked = me.checked; // More generic with all node types ?
    $.each(others, function(i, n) {
        $(n).attr('disabled', is_checked);
    });
};

creme.utils.converters.register('creme.graphael.BargraphData', 'jqplotData', function(data) {
    var ticks = data['x'] || [];
    var values = data['y'] || [];
    var jqplotData = [];

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


//creme.reports.exportReport = function(link, report_id, title) {
creme.reports.exportReport = function(title, filterform_url, export_preview_url, export_url) {
//    var filterform_url = '/reports/export/filter/%d'.format(report_id)

    // The export view uses the 'callback_url' feature of inner_popup (maybe only used here).
    // Emulate it for this case.
    // TODO : filterform should be used as select and redirection url build in js.
    creme.dialogs.form(filterform_url, {'title': title || ''})
                 .on('frame-update', function(event, frame) {
//                      new creme.reports.PreviewController(report_id).bind(frame.delegate());
                      new creme.reports.PreviewController(export_preview_url, export_url).bind(frame.delegate());
                  })
                 .onFormSuccess(function(event, data, statusText, dataType) {
                      creme.utils.goTo($(data).attr('redirect'));
                  })
                 .open({width: 1024});
};

creme.reports.openGraphEdition = function(edition_url, graph_id, reload_uri) {
    console.warn('creme.reports.openGraphEdition() is deprecated ; use bricks & actions instead.');

    creme.blocks.form(edition_url, {blockReloadUrl: reload_uri})
                .onFormSuccess(function() {
                     $('#graph-%s .ui-creme-plotselector'.format(graph_id)).creme().widget().resetBackend();
                 }).open();
};

creme.reports.PreviewController = creme.component.Component.sub({
//    _init_: function(report) {
    _init_: function(preview_url, export_url) {
//        this._redirectUrl = '/reports/export/preview/' + report + '?%s';
//        this._downloadUrl = '/reports/export/' + report + '?%s';
        this._redirectUrl = preview_url + '?%s';
        this._downloadUrl = export_url + '?%s';

        this._listeners = {
            update:   $.proxy(this._updateHeader, this),
            redirect: $.proxy(this.redirect, this),
            download: $.proxy(this.download, this)
        };
    },

    bind: function(element) {
        if (this._header !== undefined) {
            throw 'creme.reports.PreviewController is already bound.';
        }

        var listeners = this._listeners;
        var header = this._header = $('.report-preview-header', element);

        $('select[name="date_field"]',    header).change(listeners.update);
        $('select[name="date_filter_0"]', header).change(listeners.update);

        $('button[name="generate"]', header).click(listeners.redirect);
        $('button[name="download"]', header).click(listeners.download);

        this._updateHeader();
        return this;
    },

    unbind: function(element) {
        var listeners = this._listeners;
        var header = this._header;

        if (header !== undefined) {
            $('select[name="date_field"]',    header).unbind('change', listeners.update);
            $('select[name="date_filter_0"]', header).unbind('change', listeners.update);

            $('button[name="generate"]', header).unbind('click', listeners.redirect);
            $('button[name="download"]', header).unbind('click', listeners.download);
        }

        this._header = undefined;
        return this;
    },

    _updateHeader: function() {
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

// TODO : TEMPORARY HACK !
creme.reports.toggleDaysField = function(operator, types) {
    var is_visible = operator.val() && types && types.indexOf(operator.val()) !== -1;
    var days_field = $(operator).parents('.block-form:first').find('[name=\"days\"]');

    days_field.parents('tr:first').toggleClass('hidden', !is_visible);
};

creme.reports.ChartController = creme.component.Component.sub({
    _init_: function(properties) {
        this._properties = properties || {};
    },

    initialize: function(element, initial) {
        var self = this;
        var properties = this._properties || {};
        var plot = this._plot = creme.widget.create($('.ui-creme-plotselector', element));
        var state = $.extend({}, initial);

        var setState = function(data) {
            state = self._state = $.extend({}, state, data);

            $('.graph-controls-type .graph-control-value', element).text(properties.charts[state.chart]);
            $('.graph-controls-sort .graph-control-value', element).text(properties.sorts[state.sort]);

            plot.reload(state);
        };

        var popoverContent = function(popover, choices, selected) {
            var choices = Object.entries(choices).filter(function(e) { return e[0] !== selected; });

            var choices = choices.map(function(choice) {
                var value = choice[0], label = choice[1];

                return $('<a class="popover-list-item" title="%s" alt="%s">%s</a>'.format(label, label, label)).click(function(e) {
                    e.preventDefault();
                    popover.selectAndClose(value);
                });
            });

            return choices;
        }

        var chartPopover = new creme.dialogs.Popover()
                                            .onOk(function(event, value) {
                                                setState({chart: value});
                                            });

        var sortPopover = new creme.dialogs.Popover({direction: 'right'})
                                           .onOk(function(event, value) {
                                               setState({sort: value});
                                           });

        chartPopover.fill(popoverContent(chartPopover, properties.charts, state.chart));
        sortPopover.fill(popoverContent(sortPopover, properties.sorts, state.sort));

        $('.graph-controls-type .graph-control-value', element).click(function(e) {
            e.stopPropagation();
            chartPopover.fill(popoverContent(chartPopover, properties.charts, state.chart))
                        .toggle(this);
        });

        $('.graph-controls-sort .graph-control-value', element).click(function(e) {
            e.stopPropagation();
            sortPopover.fill(popoverContent(sortPopover, properties.sorts, state.sort))
                       .toggle(this);
        });

        setState(initial);
    },

    reset: function() {
        this._plot.resetBackend();
        this._plot.reload(this._state);
    }
});

}(jQuery));
