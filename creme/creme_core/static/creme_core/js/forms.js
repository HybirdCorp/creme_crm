/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2022  Hybird

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

/* globals creme_media_url */
(function($) {
"use strict";

creme.forms = {};

/*
 * Select input tools
 */

// creme.forms.Select = {};

/* istanbul ignore next */
/*
creme.forms.Select.optionsFromData = function(data, option_label, option_value) {
    console.warn('creme.forms.Select.optionsFromData is deprecated');
    var options = [];

    option_value = (option_value !== undefined) ? option_value : 0;
    option_label = (option_label !== undefined) ? option_label : 1;

    var getter_builder = function(getter) {
        if (Object.isFunc('function')) {
            return getter;
        }

        return function(entry) {
            return entry[getter];
        };
    };

    var option_label_getter = getter_builder(option_label);
    var option_value_getter = getter_builder(option_value);

    for (var index = 0; index < data.length; ++index) {
        var entry = data[index];
        var entry_value = option_value_getter(entry);
        var entry_label = option_label_getter(entry);

        if ((entry_value === undefined) || (entry_label === undefined)) {
             continue;
        }

        options.push([entry_value, entry_label]);
    }

    return options;
};
*/

/*
creme.forms.Select.fill = function(self, options, selected) {
    console.warn('creme.forms.Select.fill is deprecated');

    if ((self === undefined) || (options === undefined)) {
        return;
    }

    var old_value = self.val();
    var value, index;
    self.empty();

    for (index = 0; index < options.length; ++index) {
        var entry = options[index];
        var entry_value = entry[0];
        var entry_label = entry[1];

        var option = $('<option/>').val(entry_value).text(entry_label);

        if (entry_value === selected) {
            option.prop('selected', 'selected');
            value = selected;
        }

        self.append(option);
    }

     if (value === undefined) {
         if (options.length > 0) {
             value = options[0][0];
         }

         if (old_value !== undefined) {
             for (index = 0; index < options.length; ++index) {
                 if (options[index][0] === old_value) {
                     value = old_value;
                     break;
                 }
             }
         }
     }

     self.val(value);
     self.trigger('change');
     return self;
};
*/

/*
 * TimePicker widget
 */
creme.forms.TimePicker = {};
creme.forms.TimePicker.init = function(self) {
    var time = creme.forms.TimePicker.timeval(self);
    var disabled = $('input[type="hidden"]', self).is('[disabled]');

    $('li.hour input[type="number"]', self).val(time.hour);
    $('li.minute input[type="number"]', self).val(time.minute);

    if (disabled) {
        $('li input[type="number"]', self).prop('disabled', true);
        $('li button', self).prop('disabled', true);
    } else {
        $('li input[type="number"]', self).on('change', function() {
                creme.forms.TimePicker.update(self);
        });
        $('li button', self).on('click', function() {
            var now = new Date();
            creme.forms.TimePicker.set(self, now.getHours(), now.getMinutes());
        });
    }
};

creme.forms.TimePicker.parseTime = function(value) {
    var values = (value !== undefined) ? value.split(':') : [];
    var hour = (values.length > 1) ? values[0] : '';
    var minute = (values.length > 1) ? values[1] : '';

    return {
        hour: hour,
        minute: minute
    };
};

creme.forms.TimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
};

creme.forms.TimePicker.timeval = function(self) {
    return creme.forms.TimePicker.parseTime($('input[type="hidden"]', self).val());
};

creme.forms.TimePicker.update = function(self) {
    var hour = $('li.hour input[type="number"]', self).val();
    var minute = $('li.minute input[type="number"]', self).val();
    $('input[type="hidden"]', self).val(hour + ':' + minute);
};

creme.forms.TimePicker.clear = function(self) {
    $('li.hour input[type="number"]', self).val('');
    $('li.minute input[type="number"]', self).val('');
    $('input[type="hidden"]', self).val('');
};

creme.forms.TimePicker.set = function(self, hour, minute) {
    $('li.hour input[type="number"]', self).val(hour);
    $('li.minute input[type="number"]', self).val(minute);
    $('input[type="hidden"]', self).val(hour + ':' + minute);
};

/*
 * DateTimePicker widget
 */
creme.forms.DateTimePicker = {};
creme.forms.DateTimePicker.init = function(self, format) {
    format = format || 'yy-mm-dd';

    var datetime = creme.forms.DateTimePicker.datetimeval(self);

    $('li.date input[type="text"]', self).val(datetime.date);
    $('li.hour input[type="number"]', self).val(datetime.hour);
    $('li.minute input[type="number"]', self).val(datetime.minute);

    $('li input[type="text"]', self).on('change propertychange keyup input paste', function() {
            creme.forms.DateTimePicker.update(self);
        });

    $('li.now button', self).on('click', function(e) {
            e.preventDefault();
            creme.forms.DateTimePicker.setDate(self, new Date());
        });

    $('li.clear button', self).on('click', function(e) {
            e.preventDefault();
            creme.forms.DateTimePicker.clear(self);
        });

    $('li.date input[type="text"]', self).datepicker({
            dateFormat:      format,
            showOn:          "button",
            buttonText:      gettext("Calendar"),
            buttonImage:     creme_media_url("images/icon_calendar.gif"),
            buttonImageOnly: true
        });
};

creme.forms.DateTimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
};

creme.forms.DateTimePicker.datetimeval = function(self) {
    return creme.forms.DateTimePicker.parseDateTime($('input[type="hidden"]', self).val());
};

creme.forms.DateTimePicker.parseDateTime = function(value) {
    var values = (value !== undefined) ? value.split(' ') : [];
    var date = (values.length > 1) ? values[0] : '';
    var time = creme.forms.TimePicker.parseTime((values.length > 1) ? values[1] : '');
    return $.extend({date: date}, time);
};

creme.forms.DateTimePicker.update = function(self) {
    var date = $('li.date input[type="text"]', self).val();
    var hour = $('li.hour input[type="number"]', self).val();
    var minute = $('li.minute input[type="number"]', self).val();
    $('input[type="hidden"]', self).val(date + ' ' + hour + ':' + minute);
};

creme.forms.DateTimePicker.clear = function(self) {
    $('li.date input[type="text"]', self).val('');
    $('li.hour input[type="number"]', self).val('');
    $('li.minute input[type="number"]', self).val('');
    $('input[type="hidden"]', self).val('');
};

creme.forms.DateTimePicker.setDate = function(self, date) {
    var hour = date.getHours();
    var minute = date.getMinutes();

    $('li.date input[type="text"]', self).datepicker('setDate', date);
    $('li.hour input[type="number"]', self).val(hour);
    $('li.minute input[type="number"]', self).val(minute);

    creme.forms.DateTimePicker.update(self);
};

creme.forms.DateTimePicker.set = function(self, year, month, day, hour, minute) {
    creme.forms.DateTimePicker.setDate(self, new Date(year, month, day, hour, minute));
};

// TODO: refactor in order the widget can be properly reload (see report.js)
creme.forms._toDualColumnMultiSelect = function(store_id, use_order, buildColumns, refreshStore, reduced) {
    // Containers
    var $div   = $('<div class="dcms_div"></div>');
    var $store = $('#' + store_id);

    // Lists
    var $available = $('<ul name="available"></ul>');
    var $chosen    = $('<ul name="chosen"></ul>');

    // Buttons
    var button_html = '<input class="dcms_button" type="button"/>';
    var $add_button    = $(button_html).attr('value', gettext("Add"));
    var $rem_button    = $(button_html).attr('value', gettext("Remove"));
    var $addall_button = $(button_html).attr('value', gettext("Add all"));
    var $remall_button = $(button_html).attr('value', gettext("Remove all"));
    var $up_button     = $(button_html).attr('value', gettext("Up"));
    var $down_button   = $(button_html).attr('value', gettext("Down"));

    if (!use_order) {
        $up_button.css('display', 'none');
        $down_button.css('display', 'none');
    }

    function cleanSelection() {
        $div.find('.dcms_focused').removeClass('dcms_focused');
    }

    function addAvailableLi(label, name, is_hidden) {
        var $li = $('<li></li>').attr('name', name).append(label).on('click', clickOnAvailable).dblclick(choseOne);

        if (is_hidden) {
            $li.hide();
        }

        $available.append($li);
    }

    function addChosenLi(label, name) {
        $chosen.append($('<li></li>').attr('name', name).append(label).on('click', clickOnChosen).dblclick(removeChosen));
    }

    function refreshButtons($sel) {
        if ($sel === undefined) {
            $add_button.prop('disabled', true);
            $rem_button.prop('disabled', true);
            $up_button.prop('disabled', true);
            $down_button.prop('disabled', true);
        } else {
            var $parent = $sel.parent();

            if ($parent.attr('name') === 'chosen') {
                $add_button.prop('disabled', true);
                $rem_button.prop('disabled', false);

                var sel_name = $sel.attr('name');

                if (sel_name === $chosen.find('li').first().attr('name')) {
                    $up_button.prop('disabled', true);
                } else {
                    $up_button.prop('disabled', false);
                }

                if (sel_name === $chosen.find('li').last().attr('name')) {
                    $down_button.prop('disabled', true);
                } else {
                    $down_button.prop('disabled', false);
                }
            } else { // $available list
                $add_button.prop('disabled', false);
                $rem_button.prop('disabled', true);
                $up_button.prop('disabled', true);
                $down_button.prop('disabled', true);
            }
        }

        var chosenCount = $chosen.find('li').length;

        if (chosenCount === 0) {
            $remall_button.prop('disabled', true);
        } else {
            $remall_button.prop('disabled', false);
        }

        if (($available.find('li').length - chosenCount) === 0) {
            $addall_button.prop('disabled', true);
        } else {
            $addall_button.prop('disabled', false);
        }
    }

    function refreshWidget($sel) {
        refreshStore($store, $chosen);
        refreshButtons($sel);
    }

    function choseOne() {
        var $sel = $available.find('.dcms_focused');
        addChosenLi($sel.html(), $sel.attr('name')); // not "$sel.text()" (xss)
        $sel.hide();

        refreshWidget();
    }

    function choseAll() {
        $available.find('li').each(function() {
            var name = $(this).attr('name');

            if ($chosen.find('li[name="' + name + '"]').length === 0) {
                addChosenLi($(this).html(), name);  // not "$(this).text()" (xss)
                $(this).hide();
            }
        });

        refreshWidget();
    }

    function removeChosen() {
        var $sel = $chosen.find('.dcms_focused');
        $available.find('[name="' + $sel.attr('name') + '"]').show();
        $sel.remove();

        refreshWidget();
    }

    function removeAllChosen() {
        $chosen.empty();
        $available.find('li').each(function() {
            $(this).show();
        });

        refreshWidget();
    }

    function putChosenUp() {
        var $sel  = $chosen.find('.dcms_focused');
        var $prev = $chosen.find('.dcms_focused').prev();
        $sel.insertBefore($prev);

        refreshWidget($sel);
    }

    function putChosenDown() {
        var $sel  = $chosen.find('.dcms_focused');
        var $next = $chosen.find('.dcms_focused').next();
        $sel.insertAfter($next);

        refreshWidget($sel);
    }

    function clickOnAvailable() {
        cleanSelection();
        $(this).addClass('dcms_focused');

        refreshButtons($(this));
    }

    function clickOnChosen() {
        cleanSelection();
        $(this).addClass('dcms_focused');

        refreshButtons($(this));
    }

    function toggleRow() {
        $('.buttons a', $layout).toggleClass('view_more view_less');
        $layout.toggleClass('reduced');
    }

    buildColumns($store, addAvailableLi, addChosenLi);

    var $buttons = $('<div></div>').append($add_button.on('click', choseOne))
                                   .append($rem_button.on('click', removeChosen))
                                   .append('<br/>')
                                   .append($addall_button.on('click', choseAll))
                                   .append($remall_button.on('click', removeAllChosen))
                                   .append('<br/>')
                                   .append($up_button.on('click', putChosenUp))
                                   .append($down_button.on('click', putChosenDown));
    refreshButtons();

    $store.css('display', 'none');
    $store.replaceWith($div);

    var $layout = $('<table></table>');
    var $div_display = $('<div class="buttons"></div>').append($('<a class="view_less"></a>').on('click', toggleRow));

    $('<tbody></tbody>').appendTo($layout)
                        .append($('<tr class="header"></tr>').append($('<th width="3%"></th>').append($div_display))
                                                             .append($('<th class="available more"></th>').append(gettext("Available")))
                                                             .append($('<th class="buttons more"></th>'))
                                                             .append($('<th class="chosen more"></th>').append(gettext("Chosen")))
                                                             .append($('<th class="less"></th>').append(gettext("Select"))))
                        .append($('<tr class="content"></tr>').append($('<td></td>'))
                                                              .append($('<td class="available"></td>').append($available))
                                                              .append($('<td class="buttons"></td>').append($buttons))
                                                              .append($('<td class="chosen"></td>').append($chosen)));

    $div.append($store).append($layout);

    // Set the same dimensions for the 2 columns
    var height = Math.max($available.height() + $chosen.height(), $buttons.height());

    if (height !== 0) { // TODO: Problem with inner popups (computed dimensions are always 0) ....
        $chosen.height(height);
        $available.height(height);

        var width = Math.max($available.width(), $chosen.width());
        $chosen.width(width);
        $available.width(width);
    } else {
        $chosen.css('min-height', 200);
        $available.css('min-height', 200);
    }

    if (reduced === true) {
        toggleRow();
    }
};

creme.forms.toOrderedMultiSelect = function(table_id, reduced) {
    function buildColumns($table, addAvailableLi, addChosenLi) {
        var selected_tmp = [];

        $table.find('tr').each(function(i) {
            var $this   = $(this);
            var checked = $this.find('.oms_check').is(':checked');
            var label   = $this.find('.oms_value').html();  // not ".text()" (can cause xss)
            var li_name = 'oms_row_' + i;

            if (checked === true) {
                addAvailableLi(label, li_name, true);
                selected_tmp.push([$this.find('.oms_order').attr('value'), label, li_name]);  // [order, label, name]
            } else {
                addAvailableLi(label, li_name, false);
            }
        });

        selected_tmp.sort(function(a, b) { return a[0] - b[0]; });  // sort by order value

        for (var i = 0; i < selected_tmp.length; ++i) {
            addChosenLi(selected_tmp[i][1], selected_tmp[i][2]);
        }
    }

    function refreshTable($table, $chosen) {
        var chosenMap = {};

        $chosen.find('li').each(function(i) {
            chosenMap[$(this).attr('name')] = i + 1;
        });

        $table.find('tr').each(function(i) {
            var $this = $(this);
            var order = chosenMap[$this.attr('name')];

            if (order !== undefined) {
                $this.find('.oms_check').prop('checked', true);
                $this.find('.oms_order').attr('value', order);
            } else {
                $this.find('.oms_check').prop('checked', false);
                $this.find('.oms_order').attr('value', '');
            }
        });
    }

    creme.forms._toDualColumnMultiSelect(table_id, true, buildColumns, refreshTable, reduced);
};

// TODO : create a real widget instead
creme.forms.toImportField = function(table_id, target_query, speed) {
    speed = speed !== undefined ? speed : 'normal';

    var $table = $('#' + table_id);
    var $csv_select    = $table.find('.csv_col_select');
    var $fields_select = $table.find(target_query);

    function not_in_csv() {
        return $csv_select.val() === '0';
    }

    if (not_in_csv()) {
        $fields_select.hide();
    }

    function handleColChange() {
        if (not_in_csv()) {
            $fields_select.hide(speed);
        } else {
            $fields_select.show(speed);
        }
    }

    $csv_select.on('change', handleColChange);
};

// TODO : create a real form controller with better lifecycle (not just a css class) and
//        factorize some code with creme.dialog.FormDialog for html5 validation.
creme.forms.initialize = function(form) {
    if (form.is(':not(.is-form-active)')) {
        form.addClass('is-form-active');

        // HACK : By default the browser aligns the page to the top position of the invalid HTML5 field.
        //        and it will be hidden by the fixed header menu.
        //        This listener will force browser to scroll from the BOTTOM (false argument) and "solve" the problem.
        $('input,select,textarea', form).on('invalid', function(e) {
            this.scrollIntoView(false);
            $(e.target).addClass('is-field-invalid');
        });

        // HACK : Prevent multiple submit and also preserve <button type="submit" value="..."/> behaviour in wizards.
        form.on('click', '[type="submit"]', function(e) {
            var button = $(this);

            // A submit input/button can force deactivation of html5 validation.
            if (button.is('[data-no-validate]')) {
                form.attr('novalidate', 'novalidate');
            }

            var isHtml5Valid = Object.isEmpty(form.validateHTML5());

            if (isHtml5Valid === true) {
                if (button.is(':not(.is-form-submit)')) {
                    button.addClass('is-form-submit');
                } else {
                    e.preventDefault();
                }
            }
        }).on('submit', function() {
            form.find('[type="submit"]').addClass('is-form-submit');
        });

        creme.utils.scrollTo($('.errorlist:first, .non_field_errors', form));
    }
};


creme.forms.validateHtml5Field = function(field, options) {
    options = options || {};
    var errors = {};

    if (options.noValidate || field.is('[novalidate]')) {
        return errors;
    }

    if (field.is(':invalid')) {
        var message = field.get(0).validationMessage || '';

        errors[$(field).prop('name')] = message;

        field.addClass('is-field-invalid');
        field.trigger('html5-invalid', [true, message]);
    } else {
        field.removeClass('is-field-invalid');
        field.trigger('html5-invalid', [false]);
    }

    return errors;
};

creme.forms.validateHtml5Form = function(form, options) {
    options = options || {};
    var errors = {};
    var fieldOptions = {
         noValidate: options.noValidate || form.is('[novalidate]')
    };

    $('input, select, textarea, datalist, output', form).each(function() {
        $.extend(errors, creme.forms.validateHtml5Field($(this), fieldOptions));
    });

    return errors;
};
}(jQuery));
