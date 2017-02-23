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
 * Requires : jQuery lib, creme.utils
 */

creme.merge = creme.merge || {};

creme.merge.selectOtherEntityNRedirect = function(model_id, selection_url, merge_url) {
    var selection_url = selection_url;
    if (selection_url === undefined) {
        console.warn('creme.lv_widget.selectOtherEntityNRedirect(): implicit "selection_url" argument is deprecated ; give the URL as second argument.');
        selection_url = '/creme_core/entity/merge/select_other/';
    }

    var merge_url = merge_url;
    if (merge_url === undefined) {
        console.warn('creme.lv_widget.selectOtherEntityNRedirect(): implicit "merge_url" argument is deprecated ; give the URL as third argument.');
        merge_url = '/creme_core/entity/merge/';
    }

//    var url = '/creme_core/entity/merge/select_other/' + model_id;
//    var action = creme.lv_widget.listViewAction(url, {multiple: false});
    var action = creme.lv_widget.listViewAction(selection_url + '?' + $.param({id1: model_id}), {multiple: false});

    action.onDone(function(event, data) {
//        window.location.href = '/creme_core/entity/merge/' + model_id + ',' + data[0];
        window.location.href = merge_url + '?' + $.param({id1: model_id, id2: data[0]});
    });

    return action.start();
};

creme.merge.initializeMergeForm = function(form) {
    var getter = function(input) {
        if (input.is('input[type="checkbox"]')) {
            return input.prop('checked');
        } else if (input.is('input, select, textarea')) {
            return input.val();
        } else if (input.is('.ui-creme-widget')) {
            return input.creme().widget().val();
        }
    }

    var setter = function(input, value) {
        if (input.is('input[type="checkbox"]')) {
            input.prop('checked', value);
        } else if (input.is('input, select, textarea')) {
            input.val(value).change();
        } else if (input.is('.ui-creme-widget')) {
            input.creme().widget().val(value);
        }
    }

    var copyTo = function(source, dest) {
        setter(dest, getter(source));
    }

    form.each(function() {
        var button_html = '<input type="button" />';
        var li_html = '<li class="li_merge_button"></li>';

        $(this).find('.merge_entity_field').each(function() {
            var $result_li = $('.li_merge_result', this);
            var name = $(this).attr('name');

            var $merged = $('[name="' + name + '_merged"]', this);
            var $source_A = $('[name="' + name + '_1"]', this);
            var $source_B = $('[name="' + name + '_2"]', this);

            // jquery 1.9x migration : avoid attr('value') for inputs. 
            $result_li.before($(li_html).append($(button_html).val('>').click(function() {
                copyTo($source_A, $merged);
            })));
            $result_li.after($(li_html).append($(button_html).val('<').click(function() {
                copyTo($source_B, $merged);
            })));
        });
    });
};
