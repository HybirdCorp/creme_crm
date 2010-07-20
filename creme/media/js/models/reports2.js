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

/*
 * Requires : creme, jQuery, creme.utils, creme.ajax
 */

if(!creme.reports) creme.reports = {};

creme.reports.loadColumns = function(options)
{
    if(!options || options == undefined) return;

    $(options.show_after_ct).show();//Hide & flush values when empty label selected ?
    
    var ct_id = $(options.ct).val();
    var $hf   = $(options.hf);
    this.loadHeaderFilters(ct_id, $hf);

    var $filter   = $(options.filter);
    this.loadFilters(ct_id, $filter);

}

//Could use creme.forms.Select.optionsFromData & creme.forms.Select.fill with a hack for default/error options?
creme.reports.__loadFilters = function(url, ct_id, $target_select, parameters)
{
    if(!ct_id || ct_id == undefined || $target_select.size() != 1) return;

    var params = $.extend({
        'err_label' : 'Aucun disponible',//TODO:i18n
        'always_option': null,//Always the 1st <option /> in non-empty success cases
        'empty_option' : null,
        'error_option' : null
    }, parameters);

    var $def_option = $('<option value="">'+params.err_label+'</option>');

    var success_cb = function(data, textStatus, req){
        $target_select.empty();

        if(data.length == 0 && !params.empty_option){
            $target_select.append($def_option);
        }
        if(data.length == 0 && params.empty_option){
            $target_select.append(params.empty_option);
        }
        if(data.length > 0 && params.always_option)
        {
            $target_select.append(params.always_option);
        }

        for(var i in data)
        {
            var d = data[i];
            $target_select.append($('<option value="'+d.pk+'">'+d.fields.name+'</option>'));
        }
    };

    var error_cb = function(req, textStatus, err){
        if(!params.err_option)
        {
            $target_select.empty().append($def_option);
        }
        else
        {
            $target_select.empty().append(params.empty_option);
        }
    };

    var options = {
        beforeSend : function(request){
              creme.utils.loading('loading', false, {});
          },
        complete:function (XMLHttpRequest, textStatus) {
              creme.utils.loading('loading', true, {});
          }
    };

    creme.ajax.json.get(url+ct_id, {}, success_cb, error_cb, false, options);
}

creme.reports.loadHeaderFilters = function(ct_id, $target_select)
{
    var url = '/creme_core/header_filter/get_4_ct/';
    var params = {
        'always_option': $('<option value="">Aucune vue sélectionnée</option>'),
    };
    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}

creme.reports.loadFilters = function(ct_id, $target_select)
{
    var url = '/creme_core/filter/get_4_ct/';

    var $all_opt = $('<option value="">Tout</option>');

    var params = {
        'empty_option' : $all_opt,
        'always_option': $all_opt,
        'error_option' : $all_opt
    };

    creme.reports.__loadFilters(url, ct_id, $target_select, params);
}
