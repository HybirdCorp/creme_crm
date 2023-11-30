/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2023  Hybird

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

(function($) {
 "use strict";

function getFieldValue(input) {
    if (input.is('input[type="checkbox"]')) {
        return input.prop('checked');
    } else if (input.is('input, select, textarea')) {
        return input.val();
    } else if (input.is('.ui-creme-widget')) {
        return input.creme().widget().val();
    }
};

function setFieldValue(input, value) {
    if (input.is('input[type="checkbox"]')) {
        input.prop('checked', value);
    } else if (input.is('input, select, textarea')) {
        input.val(value).trigger('change');
    } else if (input.is('.ui-creme-widget')) {
        input.creme().widget().val(value);
    }
};

creme.initializeMergeForm = function(element) {
    function createButton(options) {
        return $((
           '<li class="merge-field-button">' +
                '<button type="button" data-from="${from}" data-to="${to}">' +
                     '<div class="merge-${direction}-arrow"></div>' +
                '</button>' +
           '</li>'
        ).template(options));
    }

    element.on('click', '.merge-field-button button', function(e) {
        e.preventDefault();
        var source = element.find('#' + $(this).data('from'));
        var target = element.find('#' + $(this).data('to'));
        setFieldValue(target, getFieldValue(source));
    });

    element.find('.merge-field[id]').each(function() {
        var resultField = $(this).find('.merge-field-result');
        var id = $(this).attr('id');
        resultField.before(createButton({direction: 'right', from: id + '_1', to: id + '_merged'}));
        resultField.after(createButton({direction: 'left', from: id + '_2', to: id + '_merged'}));
    });
};

// Keep backward compatibility
creme.merge = creme.merge || {};
creme.merge.initializeMergeForm = creme.initializeMergeForm;

/*
creme.merge = creme.merge || {};

creme.merge.initializeMergeForm = function(form) {
    var copyTo = function(source, dest) {
        setter(dest, getter(source));
    };

    form.each(function() {
        var button_html = '<button type="button">';
//        var li_html = '<li class="li_merge_button"></li>';
        var li_html = '<li class="merge-field-button"></li>';

//        $(this).find('.merge_entity_field').each(function() {
        $(this).find('.merge-field').each(function() {
//            var $result_li = $('.li_merge_result', this);
            var $result_li = $('.merge-field-result', this);
            var name = $(this).attr('name');

            var $merged = $('[name="' + name + '_merged"]', this);
            var $source_A = $('[name="' + name + '_1"]', this);
            var $source_B = $('[name="' + name + '_2"]', this);

            // jquery 1.9x migration : avoid attr('value') for inputs.
            // TODO: use an icon font (like "foundation")?

            // $result_li.before($(li_html).append($(button_html).val('⏵').on('click', function() {
            //     copyTo($source_A, $merged);
            // })));
            // $result_li.after($(li_html).append($(button_html).val('⏴').on('click', function() {
            //     copyTo($source_B, $merged);
            // })));

            $result_li.before(
                $(li_html).append(
                    $(button_html).on('click', function() {
                        copyTo($source_A, $merged);
                    }).append('<div class="merge-right-arrow" />')
                )
            );
            $result_li.after(
                $(li_html).append(
                    $(button_html).on('click', function() {
                        copyTo($source_B, $merged);
                    }).append('<div class="merge-left-arrow" />')
                )
            );
        });
    });
};
*/
}(jQuery));
