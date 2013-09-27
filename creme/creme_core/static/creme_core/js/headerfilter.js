/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2013  Hybird

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

creme.headerfilter = creme.headerfilter || {}

creme.headerfilter.HeaderFilter = function(div_id, samples) {
    var div = this.div = $('#' + div_id);
    this.store = div.find('input.inner_value');
    this.samples = $(samples);

    this.column_titles = {};
    this.columns = [];
    this.header_labels;
//     this.header_filters;
    this.underlays = {};

    this.init();
};

creme.headerfilter.HeaderFilter.prototype = {
    init: function() {
        this._initSelectorCheck();
        this._initSelectorFilters();
        this._initSelectorUnderlays();
        this._initPreviewTable();
    },

    updateStore: function() {
        this.store.attr('value', this.columns);
    },

    updatePreview: function() {
        var div = this.div;
        var length = this.columns.length;
        var preview_title;

        if (length == 0)
            preview_title = gettext('Preview');
        else if (length == 1)
            preview_title = gettext('Preview of the column');
        else
            //TODO: ngettext ??
            preview_title = gettext('Preview and order of the %s columns').format(length);

        div.find('.preview_title').text(preview_title);
        div.find('.help_instructions').text(length == 0 ? gettext('The preview is empty. Select some fields and relationships to add some columns.')
                                                        : gettext('Drag and drop the columns to order them.')
                                           );
    },

    findUnderlayInfo: function(column) {
        var underlay_info;
        var sep_index = column.indexOf('__');

        //TODO: should we populate all underlays models (so subfield would mean -> always search in underlays cache)
        if (sep_index != -1) { //this is a sub-field
            var selector;
            var fk_fieldname = column.slice(0, sep_index);
            underlay = this.underlays[fk_fieldname];

            if (!underlay) { //the underlay model is not in the cache
                selector = this.div.find('.selector_list .selector[data-column=' + fk_fieldname + ']');
                underlay = selector.find('.underlay-container');
            } else {
                selector = underlay.data('underlay_selector');
            }

            underlay_info = {'selector': selector,
                             'content':  underlay.find('.underlay-content')
                            };
        }

        return underlay_info;
    },

    onColumnChanged: function(checkbox) {
        var self = this;
        var div = this.div;
        var columns = this.columns;
//         var header_filters = this.header_filters;
        var column = checkbox.parentNode.getAttribute ('data-column');

        if (checkbox.checked) { // add the column
            var column_titles = this.column_titles;

            columns.push(column);
            this.header_labels.append($('<th>').attr('data-column', column)
                                               .append($('<input type="checkbox" checked class="preview_column_toggle" />')
                                                        .bind('change', function (event) {
                                                                var underlay_info = self.findUnderlayInfo(column);
                                                                var selectors = underlay_info ? underlay_info.content.find('.underlay_selector_list')
                                                                                            : div.find('.selector_list');

                                                                selectors.find('.selector[data-column=' + column + '] input[type=checkbox]:checked')
                                                                         .attr('checked', false)
                                                                         .change();
                                                            })
                                                        .attr('title', gettext("Remove the column '%s'").format(column_titles[column]))
                                                )
                                                .append($('<span>').addClass('dragtable-drag-handle').text(column_titles[column]))
                                     );

//             var header_filter = $('<td>').attr('data-column', column);
//             header_filters.append(header_filter);

// //              if (column == 'comment')
// //                  header_filter.append ('<select class="header_filter"><option>1</option><option>2</option></select>');
// //              else if (column == 'persons-object_inactive_customer')
// //                  header_filter.append ('<select class="header_filter"><option>Client 1</option><option>Client 2</option><option>Client 3</option><option>Client 4</option></select>');
// //              else
//             header_filter.append('<input class="header_filter" type="search" placeholder="%s" />'.format(gettext("FILTER")));

            var lists = div.find('.preview_table .preview_row');
            var samples = this.samples;
            for (var i = 0; i < samples.length; ++i) {
                var text = samples[i][column];

                if (text === '')
                    text = '—';
                else if (text === undefined)
                    text = '[…]';

                $('<td>').attr('data-column', column).html(text).appendTo(lists[i]);
            }
        } else { // remove the column
            div.find('.preview_table [data-column=' + column + ']').remove();

            var index = columns.indexOf(column);
            columns.splice(index, 1);
        }

        this.updatePreview();

        // manage subfield count
        var underlay_info = this.findUnderlayInfo(column);
        if (underlay_info) { //column is a subfield
            var checkboxes = underlay_info.content.find('input[type=checkbox]');
            var selected_checkboxes = checkboxes.filter(':checked');

            underlay_info.selector.find('.selected_count').remove();
            if (selected_checkboxes.length)
                $('<span>').addClass('selected_count')
                           .text(' (' + selected_checkboxes.length + ' / ' + checkboxes.length + ')')
                           .appendTo(underlay_info.selector);
        }

        this.updateStore();
    },

    onDragChange: function(e) {
        this.columns = $.map(this.div.find('.preview_table_header th'), function (e, i) {
            return $(e).attr('data-column');
        });

        this.updateStore();
    },

    findLastItemOfLine: function(selector) {
        var selectorY = selector.position().top;
        var firstItemOfNextLine = false;

        selector.nextAll('.selector').each(function(i, e) {
            if (firstItemOfNextLine)
                return;

            var elem = $(e);

            if (elem.position().top != selectorY)
                firstItemOfNextLine = elem;
        });

        return firstItemOfNextLine ? firstItemOfNextLine.prevAll('.selector').first() // last selector before next line
                                   //we select only the direct children to avoid sub field (that are not in the line)
                                   : selector.parent('.selector_list').find('> .selector').last(); // last selector of last line
    },

    placeUnderlay: function(underlay, lastItemOfLine) {
        underlay.insertAfter(lastItemOfLine);

        if (!underlay.__underlay_height)
            underlay.__underlay_height = underlay.height();
        underlay.css('max-height', underlay.__underlay_height);

//        TODO: uncomment after updating to an horizontal menu, to support full-width underlays
//        var position = underlay.position();
//        if (position.left != 0)
//            underlay.css ('left', -position.left + 'px');
    },

//     TODO: uncomment when secondary_relationships
//     onSubSelectorContentTypeChanged: function (target) {
//         var root = target.parents('.underlay-content');
// 
//         root.find('.selector:not(.'+ target.val() + ') input[type=checkbox]:checked')
//             .attr('checked', false)
//             .change();
// 
//         var field = root.parents ('.underlay').attr ('data-column');
// 
//         root.parents('.selector_list')
//             .find('.selector[data-column=' + field + '] .selected_count')
//             .remove();
// 
//         var valid_fields = root.find('.selector:.'+ target.val())
//                                .css('display', 'block');
// 
//         root.find('.selector:not(.'+ target.val() + ')')
//             .css ('display', 'none');
//         target.parents('.selector_title')
//               .find('.field_count')
//               .text(valid_fields.length);
//     },

    _initSelectorCheck: function() {
        var self = this;
        var div = this.div;
        var column_titles = this.column_titles;
        var header_labels = this.header_labels = div.find('.preview_table_header .sortable_header');
//         var header_filters = this.header_filters = div.find('.preview_table_header .filterable_header');

        div.find('.selector_list .selector[data-column]').each(function (i, e) {
            var el = $ (e);
            var links = el.find('.sub_selector_toggle');

            var textSource = links.length ? links : el;
            var text = textSource.text();

            if (el.parent().is('.underlay_selector_list'))
                text = column_titles[el.parents('.selector').attr('data-column')] + ' — ' + text;

            column_titles[el.attr('data-column')] = text.trim();
        });

        div.find('.selector_list input[type=checkbox]').bind('change', function (event) {
            self.onColumnChanged(event.target);
        });

        // check the boxes in the order given by our hidden input (store)
        var value = this.store.attr('value');

        if (value) {
            var to_check = value.split(',');

            this.store.attr('value', ''); //reset the value, that will be recreated by calls to onColumnChanged()

            // build a list of that will contains the checkboxes in the rigth order
            var checkboxes = [];
            for (var i in to_check) {
                checkboxes.push(undefined);
            }

            div.find('.selector_list input[type=checkbox]').each(function(i, e) {
                var index = to_check.indexOf(e.parentElement.getAttribute('data-column'));

                if (index != -1) {
                    checkboxes[index] = e;
                }
            });

            for (var i in checkboxes) {
                var checkbox = checkboxes[i];

                if (checkbox) {
                    $(checkbox).attr('checked', true).change();
                }
            }
        } else {
            this.updatePreview();
        }
    },

    _initPreviewTable: function() {
        var div = this.div;
        var underlays = this.underlays;

        div.find('.remove_all_columns').click(function(e) {
            e.preventDefault();
            div.find('.selector input[type=checkbox]:checked')
               .attr('checked', false)
               .change();

            for (var column in underlays)
               underlays[column].find('.selector input[type=checkbox]:checked')
                                .attr('checked', false)
                                .change();
        });

        var self = this;

        div.find('.preview_table')
           .dragtable({dataHeader: 'data-column',
                       change: function(event) {self.onDragChange(event);}
                      });
    },

    _initSelectorFilters: function() {
        var div = this.div;

        div.find('.field_selector_filter').each(function() {
            var elem = $(this);

            elem.data('oldVal', elem.val());

            var type = elem.attr('data-type');

            elem.bind('propertychange keyup input paste', function() {
                var val = elem.val();

                if (elem.data('oldVal') == val)
                   return;

                elem.data('oldVal', val);

                val = val.toLowerCase();

                // TODO: split-up field/relationships to be cleaned
                if (type == 'relationships') {
                    if (val == '') {
//                         TODO: when secondary_relationships
//                         $('.secondary_relationship').css ('display', 'none');
//                         $('.relationship_selectors .selector_list .selector:not(.secondary_relationship)').css ('display', 'inline-block');
                        div.find('.relationship_selectors .selector_list .selector')
                           .css('display', 'inline-block');
                        div.find('.relationship_selectors .filter_result').text('');
                    } else {
                        var total_count = 0;
                        var matches_count = 0;

                        div.find('.relationship_selectors .selector_list .selector').each(function (i, element) {
                            var item = $(element);
                            var text = item.text().toLowerCase();

                            if (text.indexOf(val) == -1) {
                                item.css('display', 'none');
                            } else {
                                item.css('display', 'inline-block');
                                matches_count += 1;
                            }

                            total_count += 1;
                        });

                        div.find('.relationship_selectors .filter_result')
                           .text(gettext('%s result(s) on %s').format(matches_count, total_count)); //TODO: keyword format
                    }
                } else {
                    div.find('.field_selectors .selector_list .selector').each(function(i, element) {
                       var item = $(element);
                       var text = item.text().toLowerCase();

                       // TODO: probably better to add a css class defining the style of a matching item compared to one that doesn't match
                       item.css('opacity', text.indexOf(val) == -1 ? 0.4 : 1);

     //                  var is_basic_field = item.parents ('.basic_field_selectors').length > 0;
     //                  item.css ('display', text.indexOf (val) == -1 ? 'none' : is_basic_field ? 'block' : 'inline-block');
                    });
                }
            });
         });

//         TODO: uncomment when secondary_relationships
//         $('.relationship_filter_all').click (function (e) {
//             e.preventDefault();
// 
//             var display = $('.secondary_relationship').css ('display');
//             $('.secondary_relationship').css ('display', display == 'none' ? 'inline-block' : 'none');
//         });
    },

    _initSelectorUnderlays: function() {
        var self = this;
        var div = this.div;
        var underlays = this.underlays;

        div.find('.sub_selector_toggle').click(function(e) {
            e.preventDefault();

            var target = $(e.target);
            var selector = target.parent('.selector');
            var column = selector.attr('data-column');

            var underlay = underlays[column];
            if (!underlay) {
                underlays[column] = underlay = $('<div>').attr('data-column', column)
                                                         .addClass('underlay')
// TODO: uncomment after updating to an horizontal menu, to support full-width underlays
//                                                       .css('width', $(window).width())
                                                         .data('underlay_selector', selector)
                                                         .append(selector.find('.underlay-container'));
            }

            var lastItemOfLine = self.findLastItemOfLine(selector);
            var container = selector.parents('.selector_list').find('.underlay'); // only 1 underlay per list

            if (container.length == 0)  {
                self.placeUnderlay(underlay, lastItemOfLine);

                // underlay opening: sliding in animation
                underlay.children().css ('opacity', 1);
                underlay.find('.underlay-content').css('opacity', 0);
                underlay.css('max-height', 0).css('opacity', 1);

                var targetHeight = underlay.__underlay_height;

                // animation version 1
    //            underlay.children().delay (100).animate ({opacity: 1}, 400);
    //            underlay.animate ({'max-height': targetHeight}, 300, function () {
    //                underlay.css ('width', $(window).width());
    //            });

                underlay.find('.underlay-content').animate({opacity: 1}, 400);
                underlay.children().delay (100).animate({opacity: 1}, 400);
                underlay.animate({'max-height': targetHeight}, 300, function() {
                    // TODO: uncomment after updating to an horizontal menu, to support full-width underlays
                    // underlay.css('width', $(window).width());
                });
            } else if (container.attr('data-column') == column) {
                // underlay closing: sliding out animation

                // animation version 1
    //            container.children().animate ({opacity: 0}, 150);
    //            container.animate ({'max-height': 0}, 300, function (e) {
    //                container.detach();
    //            });

                container.find('.underlay-content').animate({opacity: 0}, 150);
                container.children().delay(130).animate({opacity: 0}, 150);
                container.animate({'max-height': 0}, 300, function(e) {
                    container.detach();
                });
            } else {
                // underlay transition : cross-fade animation
                container.animate({opacity: 0}, 100, function(e) {
                    container.detach();

                    underlay.css('opacity', 0);
                    self.placeUnderlay(underlay, lastItemOfLine);

                    // animation version 1
    //                underlay.animate ({opacity: 1}, 150);
    //                underlay.children().animate ({opacity: 1}, 150);

                    underlay.animate({opacity: 1}, 150);
                    underlay.find('.underlay-content').animate({opacity: 1}, 150);
                    underlay.children().animate({opacity: 1}, 150);
                });
            }

            // TODO: uncomment after updating to an horizontal menu, to support full-width underlays
            // underlay.find('.arrow').css('left', 20 + target.position().left + 'px');
            
            var arrow = underlay.find('.arrow');
            // TODO: find a way to get the width from the arrow itself, right now, when it's showing, the width it returns is 0 instead of 17; possibly need to check with the latest jQuery
            var arrowWidth = 17; // arrow width + its left and right borders -> arrow.outerWidth()
            
            var toggleOffset = target.offset().left - target.parents('.field_selectors').offset().left;
            var arrowOffset = toggleOffset + (target.width() - arrowWidth) / 2;
            arrow.css('left', arrowOffset + 'px');
        });

//         TODO: uncomment when relationships objects sub-fields
//         div.find('.underlay-content .content_type_toggle').change(function(e) {
//             self.onSubSelectorContentTypeChanged($(e.target));
//         });
// 
//         div.find('.underlay-content .content_type_toggle').change();
    }
};
