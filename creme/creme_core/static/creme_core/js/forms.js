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

creme.forms = {}

/*
 * Select input tools
 */

creme.forms.Select = {}
creme.forms.Select.optionsFromData = function(data, option_label, option_value) {
    var options = [];

    option_value = (option_value != undefined) ? option_value : 0;
    option_label = (option_label != undefined) ? option_label : 1;

    var getter_builder = function(getter) {
        if (typeof getter == 'function')
            return getter;

        return function(entry) {return entry[getter];}
    };

    var option_label_getter = getter_builder(option_label);
    var option_value_getter = getter_builder(option_value);

    for(var index = 0; index < data.length; ++index) {
        var entry = data[index];
         var entry_value = option_value_getter(entry);
         var entry_label = option_label_getter(entry);

         if ((entry_value == undefined) || (entry_label == undefined))
             continue;

        options.push([entry_value, entry_label]);
    }

    return options;
}

creme.forms.Select.fill = function(self, options, selected) {
    if ((self == undefined) || (options == undefined)) {
        return;
    }

    var old_value = self.val();
    var value;
    self.empty();

     for(var index = 0; index < options.length; ++index) {
         var entry = options[index];
         var entry_value = entry[0];
         var entry_label = entry[1];

         option = $('<option/>').val(entry_value).text(entry_label);

         if (entry_value == selected) {
             option.attr('selected', 'selected');
             value = selected;
         }

         self.append(option);
     }

     if (value == undefined) {
         if (options.length > 0) {
             value = options[0][0];
         }

         if (old_value != undefined) {
             for(var index = 0; index < options.length; ++index)    {
                 if (options[index][0] == old_value) {
                     value = old_value;
                     break;
                 }
             }
         }
     }

     self.val(value);
     self.change();
     return self;
}

/*
 * TimePicker widget
 */
creme.forms.TimePicker = {}
creme.forms.TimePicker.init = function(self) {
    var time = creme.forms.TimePicker.timeval(self);

    $('li.hour input[type="text"]', self).val(time.hour);
    $('li.minute input[type="text"]', self).val(time.minute);

    $('li input[type="text"]', self).bind('change', function() {
            creme.forms.TimePicker.update(self);
        });

    $('li button', self).bind('click', function() {
            var now = new Date();
            creme.forms.TimePicker.set(self, now.getHours(), now.getMinutes());
        });
}

creme.forms.TimePicker.parseTime = function(value) {
    var values = (value != undefined) ? value.split(':') : [];
    var hour = (values.length > 1) ? values[0] : '';
    var minute = (values.length > 1) ? values[1] : '';

    return {hour:hour, minute:minute};
}

creme.forms.TimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
}

creme.forms.TimePicker.timeval = function(self) {
    return creme.forms.TimePicker.parseTime($('input[type="hidden"]', self).val());
}

creme.forms.TimePicker.update = function(self) {
    var hour = $('li.hour input[type="text"]', self).val();
    var minute = $('li.minute input[type="text"]', self).val();
    $('input[type="hidden"]', self).val(hour + ':' + minute);
}

creme.forms.TimePicker.clear = function(self) {
    $('li.hour input[type="text"]', self).val('');
    $('li.minute input[type="text"]', self).val('');
    $('input[type="hidden"]', self).val('');
}

creme.forms.TimePicker.set = function(self, hour, minute) {
    $('li.hour input[type="text"]', self).val(hour);
    $('li.minute input[type="text"]', self).val(minute);
    $('input[type="hidden"]', self).val(hour + ':' + minute);
}

/*
 * DateTimePicker widget
 */
creme.forms.DateTimePicker = {}
creme.forms.DateTimePicker.init = function(self) {
    var datetime = creme.forms.DateTimePicker.datetimeval(self);

    $('li.date input[type="text"]', self).val(datetime.date);
    $('li.hour input[type="text"]', self).val(datetime.hour);
    $('li.minute input[type="text"]', self).val(datetime.minute);

    $('li input[type="text"]', self).bind('change', function() {
            creme.forms.DateTimePicker.update(self);
        });

    $('li.now button', self).bind('click', function() {
            var now = new Date();
            creme.forms.DateTimePicker.set(self, now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes());
        });

    $('li.clear button', self).bind('click', function() {
//             var now = new Date();
            creme.forms.DateTimePicker.clear(self);
        });

    $('li.date input[type="text"]', self).datepicker({
            dateFormat: "yy-mm-dd",
            showOn: "button",
            buttonImage: media_url("images/icon_calendar.gif"),
            buttonImageOnly: true
        });
}

creme.forms.DateTimePicker.val = function(self) {
    return $('input[type="hidden"]', self).val();
}

creme.forms.DateTimePicker.datetimeval = function(self) {
    return creme.forms.DateTimePicker.parseDateTime($('input[type="hidden"]', self).val());
}

creme.forms.DateTimePicker.parseDateTime = function(value) {
    var values = (value != undefined) ? value.split(' ') : [];
    var date = (values.length > 1) ? values[0] : '';
    var time = creme.forms.TimePicker.parseTime((values.length > 1) ? values[1] : '');
    return $.extend({date:date}, time);
}

creme.forms.DateTimePicker.update = function(self) {
    var date = $('li.date input[type="text"]', self).val();
    var hour = $('li.hour input[type="text"]', self).val();
    var minute = $('li.minute input[type="text"]', self).val();
    $('input[type="hidden"]', self).val(date + ' ' + hour + ':' + minute);
}

creme.forms.DateTimePicker.clear = function(self) {
    $('li.date input[type="text"]', self).val('');
    $('li.hour input[type="text"]', self).val('');
    $('li.minute input[type="text"]', self).val('');
    $('input[type="hidden"]', self).val('');
}

creme.forms.DateTimePicker.set = function(self, year, month, day, hour, minute) {
    var date = year + '-' + ((month < 9) ? '0' : '') + (month + 1) + '-' + ((day < 9) ? '0' : '') + day;
    $('li.date input[type="text"]', self).val(date);
    $('li.hour input[type="text"]', self).val(hour);
    $('li.minute input[type="text"]', self).val(minute);
    $('input[type="hidden"]', self).val(date + ' ' + hour + ':' + minute);
}

/*
 * RelationSelector widget
 */

//TODO: still used in creme.reports.link_relation_report => see creme.forms.RelationSelector.contentTypeRequest(..)
creme.forms.RelationSelector = {}
/*
creme.forms.RelationSelector.openEntityInnerPopup = function(self, list) {
    var content_type = $('select[name="content_type"]', self).find('option:selected').val();
    var o2m = 0;
    var url = '/creme_core/lv_popup/' + content_type + '/' + o2m;

    creme.utils.showInnerPopup(url, {
            'send_button_label': gettext("Validate the selection"),
            'send_button': function(dialog) {
                    var lv = $('form[name="list_view_form"]');
                    var result = lv.list_view("getSelectedEntitiesAsArray");

                    if (result.length == 0) {
                        creme.utils.showDialog(gettext("Please select at least one entity."),
                                               {'title': gettext("Error")});
                        return;
                    }

                    creme.forms.RelationSelector.update(self, result[0]);

                    for(var index = 1; index < result.length; ++index) {
                        var new_selector = creme.forms.RelationList.cloneSelector(list, self);
                        creme.forms.RelationSelector.update(new_selector, result[index]);
                    }

                    creme.forms.RelationList.update(list);
                    creme.utils.closeDialog(dialog, false);
                }
        });
}

creme.forms.RelationSelector.init = function(self, predicates, content_types, entity) {
    var predicate_select = creme.forms.RelationSelector.predicateSelect(self);
    var content_type_select = creme.forms.RelationSelector.contentTypeSelect(self);

    creme.forms.Select.fill(predicate_select, predicates['options'], predicates['selected']);

    if (content_types != undefined) {
        creme.forms.Select.fill(content_type_select, content_types['options'], content_types['selected']);
    }

    if (entity != undefined) {
        creme.forms.RelationSelector.update(self, entity);
    }
}

creme.forms.RelationSelector.create = function() {
    var predicate_select = $('<select/>').attr('name', 'predicate');
    var content_type_select = $('<select/>').attr('name', 'content_type');
    var target_select = $('<button type="button"/>').attr('name', 'target').text(gettext("Selection..."));

    var relation_selector = $('<ul style="list-style:none;padding:0;margin:0;"/>').attr('id', new Date().getTime()).addClass('ui-creme-rel-selector');

    var delete_button = $('<img/>').attr('src', media_url('images/delete_22.png'))
                                   .attr('alt', gettext("Delete"))
                                   .attr('title', gettext("Delete"))

    relation_selector.append($('<li/>').append('&nbsp;').append(predicate_select))
                     .append($('<li/>').append('&nbsp;').append(content_type_select))
                     .append($('<li/>').append('&nbsp;').append(target_select))
                     .append($('<input/>').attr('type', 'hidden').val(''))
                     .append($('<li class="last"/>').append('&nbsp;').append(delete_button));

    return relation_selector;
}

creme.forms.RelationSelector.bind = function(self, list) {
    $('img', self).click(
        function() {
            $(this).parents('.ui-creme-rel-selector').remove();
            creme.forms.RelationList.update(list);
        });

    creme.forms.RelationSelector.predicateSelect(self).bind('change',
        function() {
            if ($(this).val().length > 0) {
                creme.forms.RelationSelector.updateContentTypeSelect(self);
            }
        });

    creme.forms.RelationSelector.contentTypeSelect(self).bind('change',
        function() {
            if ($(this).val().length > 0) {
                creme.forms.RelationSelector.clear(self);
                creme.forms.RelationList.update(list);
            }
        });

    creme.forms.RelationSelector.targetButton(self).click(
         function() {
             creme.forms.RelationSelector.openEntityInnerPopup(self, list);
         });
}

creme.forms.RelationSelector.predicateSelect = function(self) {
    return $('select[name="predicate"]', self);
}

creme.forms.RelationSelector.contentTypeSelect = function(self) {
    return $('select[name="content_type"]', self);
}

creme.forms.RelationSelector.targetButton = function(self) {
    return $('button[name="target"]', self);
}

creme.forms.RelationSelector.val = function(self) {
    return $('input[type="hidden"]', self).val();
}

creme.forms.RelationSelector.clear = function(self) {
    $('input[type="hidden"]', self).val('');
    creme.forms.RelationSelector.targetButton(self).text(gettext("Selection..."));
}

creme.forms.RelationSelector.update = function(self, target_id) {
    $('input[type="hidden"]', self).val('(' + creme.forms.RelationSelector.predicateSelect(self).val() + ',' + creme.forms.RelationSelector.contentTypeSelect(self).val() + ',' + target_id + ')');
    creme.forms.RelationSelector.updateTargetButtonText(self, target_id);
}

creme.forms.RelationSelector.clone = function(self) {
    var result = self.clone();
    $('select[name="predicate"]', result).val($('select[name="predicate"]', self).val());
    $('select[name="content_type"]', result).val($('select[name="content_type"]', self).val());
    return result;
}

creme.forms.RelationSelector.updateTargetButtonText = function(self, result) {
    var target = $('button[name="target"]', self);

    creme.ajax.json.get('/creme_core/relation/entity/' + result + '/json',
        {
            fields:['unicode']
        },
        function(data) {
            value = data.join('');

            if (value.length > 0) {
                target.text(data.join(''));
            } else {
                target.text('...');
            }
        },
        function(err) {
            target.text(gettext("Server unavailable: please reload the page. If the problem persists, please contact your administrator."));
        }, false);
}

creme.forms.RelationSelector.updateContentTypeSelect = function(self) {
    var content_type_select = creme.forms.RelationSelector.contentTypeSelect(self);
    var predicate_select = creme.forms.RelationSelector.predicateSelect(self);

    creme.forms.RelationSelector.targetButton(self).text(gettext("Selection..."));
    creme.forms.RelationSelector.clear(self);

    creme.forms.RelationSelector.contentTypeRequest(predicate_select.val(),
        function(options) {
            creme.forms.Select.fill(content_type_select, options);
            content_type_select.change();
        });
}
*/

//TODO: still used in creme.reports.link_relation_report
creme.forms.RelationSelector.contentTypeRequest = function(predicate, success_cb, error_cb) {
    creme.ajax.json.get('/creme_core/relation/predicate/' + predicate + '/content_types/json',
            {
                fields:['id', 'unicode'],
                sort:'name'
            }, success_cb, error_cb);
}

/*
creme.forms.RelationSelector.predicateRequest = function(subject, success_cb, error_cb, sync) {
    creme.ajax.json.get('/creme_core/relation/entity/' + subject + '/predicates/json',
            {
                fields:['id', 'unicode'],
                sort:'unicode'
            }, success_cb, error_cb, sync);
}
*/
/*
 * RelationList widget
 */

//TODO: remove when RelatedEntitiesField is removed
/*
creme.forms.RelationList = {}
creme.forms.RelationList.update = function(self) {
    var list_input = creme.forms.RelationList.input(self);
    var request = '';

    $('.ui-creme-rel-selector input[type="hidden"]', self).each( function(index) {
        entry = $(this).val();
        request += (entry.length > 0) ? entry + ';' : '';
    });

    list_input.val(request);
}

creme.forms.RelationList.input = function(self) {
    return $('#' + self.attr('widget-input'));
}

creme.forms.RelationList.init = function(self, subject) {
    if (subject != undefined) {
        creme.forms.RelationSelector.predicateRequest(subject,
                function(data) {
                    creme.forms.Select.fill($('select.predicates', self), data);
                    creme.forms.RelationList.init(self);
                });
        return;
    }

    var list_input = creme.forms.RelationList.input(self);
    var list_value = list_input.val();
    var entries = list_value.split(';');

    if ((entries == undefined) || (entries.length < 2))
        return;

    for(var index = 0; index < entries.length - 1; ++index) {
        var entry = entries[index];
        entry = entry.slice(1, entry.length - 1).split(',');
        creme.forms.RelationList.addSelector(self, entry[0], entry[1], entry[2]);
    }
}

creme.forms.RelationList.count = function(self) {
    return $('.ui-creme-rel-selector', self).size();
}

creme.forms.RelationList.__getPredicates = function(self) {
    var predicates = [];
    $('select.predicates option', self).each(function() {
            predicates.push([$(this).val(), $(this).text()]);
        });

//    predicates.sort(function(a, b) {
//            return (a[1] > b[1]) ? 1 : ((a[1] < b[1]) ? -1 : 0);
//        });

    return predicates;
}

creme.forms.RelationList.addSelector = function(self, predicate, content_type, entity) {
    // TODO : see for optimization with cloned "predicates" select
    var predicates = creme.forms.RelationList.__getPredicates(self);

    if (predicates.length == 0)
        return;

    var predicate = (predicate != undefined) ? predicate : predicates[0][0];

    creme.forms.RelationSelector.contentTypeRequest(predicate,
        function(content_types) {
            var selector = creme.forms.RelationSelector.create();
            creme.forms.RelationSelector.init(selector,
                                              {'options':predicates, 'selected':predicate},
                                              {'options':content_types, 'selected':content_type},
                                              entity);
            creme.forms.RelationSelector.bind(selector, self);
            $('div.list', self).append(selector);
        });
}

creme.forms.RelationList.cloneSelector = function(self, source) {
    var selector = creme.forms.RelationSelector.clone(source);
    creme.forms.RelationSelector.bind(selector, self);
    selector.insertAfter(source);

    creme.forms.RelationList.update(self);
    return selector;
}

creme.forms.RelationList.cloneLastSelector = function(self) {
    var last = $('.ui-creme-rel-selector:last', self);
    return creme.forms.RelationList.cloneSelector(self, last);
}

creme.forms.RelationList.appendSelector = function(self) {
    if (creme.forms.RelationList.count(self) > 0) {
        creme.forms.RelationList.cloneLastSelector(self);
    } else {
        creme.forms.RelationList.addSelector(self);
    }
}
*/
//TODO: refactor in order the widget can be properly reload (see report.js)
creme.forms._toDualColumnMultiSelect = function(store_id, use_order, buildColumns, refreshStore) {
    //Containers
    var $div   = $('<div class="dcms_div"></div>');
    var $store = $('#' + store_id);

    //Lists
    var $available = $('<ul name="available"></ul>');
    var $chosen    = $('<ul name="chosen"></ul>');

    //Buttons
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
        var $li = $('<li></li>').attr('name', name).append(label).click(clickOnAvailable).dblclick(choseOne);

        if (is_hidden) {
            $li.hide();
        }

        $available.append($li)
    }

    function addChosenLi(label, name) {
        $chosen.append($('<li></li>').attr('name', name).append(label).click(clickOnChosen).dblclick(removeChosen));
    }

    function refreshButtons($sel) {
        if ($sel == undefined) {
            $add_button.attr('disabled', 'disabled');
            $rem_button.attr('disabled', 'disabled');
            $up_button.attr('disabled', 'disabled');
            $down_button.attr('disabled', 'disabled');
        } else {
            var $parent = $sel.parent();

            if ($parent.attr('name') == $chosen.attr('name')) { /*TODO: comparison on name is ugly, but '==' and '===' don't work....*/
                $add_button.attr('disabled', 'disabled');
                $rem_button.attr('disabled', '');

                var sel_name = $sel.attr('name');

                if (sel_name == $chosen.find('li:first').attr('name')) { $up_button.attr('disabled', 'disabled');
                } else                                                 { $up_button.attr('disabled', ''); }

                if (sel_name == $chosen.find('li:last').attr('name')) { $down_button.attr('disabled', 'disabled');
                } else                                                { $down_button.attr('disabled', ''); }
            } else { //$available list
                $add_button.attr('disabled', '');
                $rem_button.attr('disabled', 'disabled');
                $up_button.attr('disabled', 'disabled');
                $down_button.attr('disabled', 'disabled');
            }
        }

        var chosenCount = $chosen.find('li').size();

        if (chosenCount == 0) { $remall_button.attr('disabled', 'disabled');
        } else                { $remall_button.attr('disabled', ''); }

        if (($available.find('li').size() - chosenCount) == 0) { $addall_button.attr('disabled', 'disabled');
        } else                                                 { $addall_button.attr('disabled', ''); }
    }

    function refreshWidget($sel) {
        refreshStore($store, $chosen);
        refreshButtons($sel);
    }

    function choseOne() {
        var $sel = $available.find('.dcms_focused');
        addChosenLi($sel.text(), $sel.attr('name'));
        $sel.hide();

        refreshWidget();
    }

    function choseAll() {
        $available.find('li').each(function() {
            var name = $(this).attr('name');

            if ($chosen.find('li[name="' + name + '"]').size() == 0) {
                addChosenLi($(this).text(), name);
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

    buildColumns($store, addAvailableLi, addChosenLi);

    var $buttons = $('<div></div>').append($add_button.click(choseOne))
                                   .append($rem_button.click(removeChosen))
                                   .append('<br/>')
                                   .append($addall_button.click(choseAll))
                                   .append($remall_button.click(removeAllChosen))
                                   .append('<br/>')
                                   .append($up_button.click(putChosenUp))
                                   .append($down_button.click(putChosenDown));
    refreshButtons();

    $store.css('display', 'none');
    $store.replaceWith($div);

    var $layout = $('<table></table>');
    $('<tbody></tbody>').appendTo($layout)
                        .append($('<tr></tr>').append($('<th></th>').append(gettext("Available")))
                                              .append($('<th></th>'))
                                              .append($('<th></th>').append(gettext("Chosen"))))
                        .append($('<tr></tr>').append($('<td></td>').append($available))
                                              .append($('<td></td>').append($buttons))
                                              .append($('<td></td>').append($chosen)));

    $div.append($store).append($layout);

    //Set the same dimensions for the 2 columns
    var width = Math.max($available.width(), $chosen.width());
    $chosen.width(width);
    $available.width(width);

    var height = Math.max($available.height() + $chosen.height(), $buttons.height());
    $chosen.height(height);
    $available.height(height);
}

creme.forms.toUnorderedMultiSelect = function(select_id) {
    function buildColumns($select, addAvailableLi, addChosenLi) { //TODO: use inheritage instead ??
        $select.find('option').each(function(i) {
            var label   = $(this).text();
            var li_name = $(this).attr('value');

            if ($(this).attr('selected') == true) {
                addAvailableLi(label, li_name, true);
                addChosenLi(label, li_name);
            } else {
                addAvailableLi(label, li_name, false);
            }
        });
    }

    function refreshSelect($select, $chosen) {
        var chosenMap = {};

        $chosen.find('li').each(function(i) {
            chosenMap[$(this).attr('name')] = true;
        });

        $select.find('option').each(function(i) {
            var is_selected = chosenMap[$(this).attr('value')];

            if (is_selected != undefined) {
                $(this).attr('selected', 'selected');
            } else {
                $(this).attr('selected', '');
            }
        });
    }

    creme.forms._toDualColumnMultiSelect(select_id, false, buildColumns, refreshSelect);
}

creme.forms.toOrderedMultiSelect = function(table_id) {
    function buildColumns($table, addAvailableLi, addChosenLi) {
        var selected_tmp = [];

        $table.find('tr').each(function(i) {
            var checked = $(this).find('.oms_check').attr('checked');
            var label   = $(this).find('.oms_value').text();
            var li_name = 'oms_row_' + i;

            if (checked == true) {
                addAvailableLi(label, li_name, true);
                selected_tmp.push([$(this).find('.oms_order').attr('value'), label, li_name]); //[order, label, name]
            } else {
                addAvailableLi(label, li_name, false);
            }
        });

        selected_tmp.sort(function(a, b) { return a[0] - b[0]; }); //sort by order value

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
            var order = chosenMap[$(this).attr('name')];

            if (order != undefined) {
                $(this).find('.oms_check').attr('checked', true);
                $(this).find('.oms_order').attr('value', order);
            } else {
                $(this).find('.oms_check').attr('checked', false);
                $(this).find('.oms_order').attr('value', '');
            }
        });
    }

    creme.forms._toDualColumnMultiSelect(table_id, true, buildColumns, refreshTable);
}

creme.forms.toCSVImportField = function(table_id) {
    var $table = $('#' + table_id);
    var $csv_select    = $table.find('.csv_col_select');
    var $fields_select = $table.find('.csv_subfields_select');

    function not_in_csv() {
        return $csv_select.find('[value="0"]').attr('selected');
    }

    if (not_in_csv()) {
        $fields_select.hide();
    }

    function handleCSVColChange() {
        if (not_in_csv()) {
            $fields_select.hide('normal');
        } else {
            $fields_select.show('normal');
        }
    }

    $csv_select.change(handleCSVColChange);
}
