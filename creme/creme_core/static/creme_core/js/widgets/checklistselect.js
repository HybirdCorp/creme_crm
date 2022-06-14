/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2013-2022  Hybird

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

(function($) {
"use strict";

creme.widget = creme.widget || {};

creme.widget.CheckListSelect = creme.widget.declare('ui-creme-checklistselect', {
    options: {
        datatype: 'string',
        less:     0
    },

    _create: function(element, options, cb, sync) {
        var self = this;

        this._converter = options.datatype === 'json' ? creme.utils.JSON.decoder({}) : null;
        this.less(element, options.less || element.is('[less]'));

//        this.disabled(element, creme.object.isTrue(options.disabled) || element.is('[disabled]'));
        this.disabled(element, creme.object.isTrue(options.disabled) || this._delegate(element).is('[disabled]'));

        this._initializeController(element, options);

        $('.checklist-create:not([disabled])', element).on('click', function(e) {
            e.preventDefault();
            self._createItem(element, $(this));
        });

        $(element).on('click', '.checklist-check-all:not([disabled])', function() {
            self.selectAll(element);
        });

        $(element).on('click', '.checklist-check-none:not([disabled])', function() {
            self.unselectAll(element);
        });

        $('.checklist-filter', element).on('propertychange keyup input paste', function() {
            self._updateViewFilter(element, $(this).val().toLowerCase());
        });

        $('.checklist-toggle-less', element).on('click', function() {
            self.toggleShowLess(element);
        });

        $(element).on('change', '.checkbox-field:not(.hidden):not([disabled]) input[type="checkbox"]', function(e) {
            var checkbox = $(this);
            self._selections.toggle(parseInt(checkbox.attr('checklist-index')), checkbox.prop('checked'));
        });

        $(element).on('click', '.checkbox-field:not(.hidden):not([disabled]) .checkbox-label', function(e) {
            e.stopPropagation();
            var checkbox = $(this).parent().find('input[type="checkbox"]');
            self._selections.toggle(parseInt(checkbox.attr('checklist-index')), !checkbox.prop('checked'));
        });

        element.addClass('widget-ready');
    },

    _getItemFilter: function(filter) {
        return function(item) {
            return (!Object.isEmpty(item.label) && item.label.toLowerCase().indexOf(filter) !== -1) ||
                   (!Object.isEmpty(item.help) && item.help.toLowerCase().indexOf(filter) !== -1);
        };
    },

    _updateViewFilter: function(element, filter) {
        var isfiltered = !Object.isEmpty(filter);
        var content = this.content(element);
        var hide = content.is('.filter');
        var filter_lambda = this._getItemFilter(filter);

        content.toggleClass('filtered', isfiltered);

        if (hide) {
            this._model.each(function(item) {
                item.visible = filter_lambda(item);
            });
        } else {
            this._model.each(function(item) {
                item.disabled = !filter_lambda(item);
            });
        }

        this._controller.redraw();

        this._updateViewCounter(element);
        this._updateViewLess(element);
    },

    _updateViewSelection: function(element) {
        var comparator = function(a, b) {
            return creme.utils.compareTo(a.value, b);
        };
        var indices = this._model.indicesOf(this.val(element) || [], comparator);

        this._selections.select(indices);
    },

    _updateViewCounter: function(element) {
        var counter = $('.checklist-counter', element);
        var selection_count = this._selections.selected().length;
        var hilighted_count = $('.checkbox-field:not(.hidden)', this.content(element)).length;
        var model_count = this._model.length();
        var messages = [];

        if (selection_count > 0) {
            messages.push(ngettext('%d selection', '%d selections', selection_count).format(selection_count));
        }

        if (hilighted_count !== model_count) {
            messages.push(ngettext('%d result of %d', '%d results of %d', hilighted_count).format(hilighted_count, model_count));
        }

        counter.toggleClass('visible', messages.length > 0)
               .html(messages.join('&nbsp;‒&nbsp;') + '&nbsp;');

        $('.checklist-check-all, .checklist-check-none', element).toggleClass('hidden', model_count < 3);
        this._updateViewLessCounter(element);
        this._updateViewErrorState(element);
    },

    _updateDelegate: function(element) {
        this._delegate(element).val(this.selected(element));
        element.trigger('change');
    },

    _updateViewLessCounter: function(element) {
        var iscollapsed = this._lessCollapsed;
        var content = this.content(element);
        var moreItems = $('.checkbox-field:not(.hidden).more input[type="checkbox"]', content);
        var moreCount = moreItems.length;
        var messages = [];

        // items are collapsed
        if (iscollapsed) {
            var moreSelectedCount = moreItems.filter(':checked').length;

            if (moreCount > 0) {
                messages.push(ngettext('%d hidden item', '%d hidden items', moreCount).format(moreCount));
            }

            if (moreSelectedCount > 0) {
                messages.push(ngettext('(with %d selection)', '(with %d selections)', moreSelectedCount).format(moreSelectedCount));
            }
        } else if (moreCount > 0) {
            messages.push(ngettext('Collapse %d item', 'Collapse %d items', moreCount).format(moreCount));
        }

        $('.checklist-toggle-less', element).html(messages.join(' '));
    },

    _updateViewLess: function(element) {
        var limit = this._lessCount;
        var iscollapsed = this._lessCollapsed;

        var content = this.content(element);
        var isfiltered = content.is('.filtered:not(.search)');
        var items = isfiltered ? $('.checkbox-field:not(.hidden)', content) : $('.checkbox-field', content);
        var isactive = items.length > limit;

        content.toggleClass('less', iscollapsed);
        $('.checklist-toggle-less', element).toggleClass('is-active', isactive);

        if (isactive) {
            items.each(function(index) {
                $(this).toggleClass('more', index >= limit);
            });
        } else {
            items.removeClass('more');
        }

        this._updateViewLessCounter(element);
    },

    _updateViewErrorState: function(element) {
        // If delegate is absent, ":invalid" will be considered as pseudo-selector.
        // Since jQuery > 1.9, ":invalid" is no longer recognized and raises an error.
        var delegate = this._delegate(element);
        var isinvalid = delegate.length > 0 && delegate.is('.is-field-invalid:invalid');

        element.toggleClass('is-field-invalid', isinvalid);
    },

    _delegate: function(element) {
        return $('select.ui-creme-input', element);
    },

    _initializeController: function(element, options) {
        var self = this;
        var disabled = this.disabled(element);
        var input = this._delegate(element);
        var content = this.content(element);

        var renderer = new creme.model.CheckGroupListRenderer();
        var controller = this._controller = new creme.model.CollectionController();
        var selections = this._selections = new creme.model.SelectionController();
        var input_renderer = new creme.model.ChoiceGroupRenderer();

        var choices = creme.model.ChoiceGroupRenderer.parse(input);
        var model = this._model = new creme.model.Array(choices);

        selections.model(model)
                  .selectionFilter(function(item, index) {
                      return !item.disabled && item.visible && !item.readonly;
                   })
                  .on('change', function() {
                      self._updateDelegate(element);
                      self._updateViewCounter(element);
                   });

        renderer.converter(this._converter)
                .disabled(disabled);

        controller.renderer(renderer)
                  .target(content)
                  .model(model)
                  .redraw();

        input_renderer.target(input)
                      .model(model);

        input.on('change', function() {
                  self._updateViewSelection(element);
              })
             .on('invalid html5-invalid', function() {
                  self._updateViewErrorState(element);
              });

        model.bind('add remove', function() {
                  self._updateViewCounter(element);
                  self._updateViewLess(element);
                  input_renderer.redraw();
              });

        this._updateViewCounter(element);
        this._updateViewLess(element);
    },

    toggleShowLess: function(element, state) {
        if (this._less) {
            this._lessCollapsed = Object.isNone(state) ? !this._lessCollapsed : state;
            this._updateViewLess(element);
        }

        return this;
    },

    isLessCollapsed: function(element) {
        return this._less && this._lessCollapsed;
    },

    lessCount: function(element) {
        return this._lessCount;
    },

    less: function(element, less) {
        if (less === undefined) {
            return this._less;
        }

        var isLess = less > 0 || Boolean(less);

        this._lessCount = less > 1 ? less : 10;
        this._less = isLess;
        this.toggleShowLess(element, this._less);

        return this;
    },

    disabled: function(element, disabled) {
        if (disabled === undefined) {
            return this._disabled;
        }

        element.toggleAttr('disabled', disabled);  // TODO: remove (invalid attribute for div)
        element.toggleClass('is-disabled', disabled);
        this._disabled = disabled;

        $(
            '.checklist-check-all, .checklist-check-none, .checklist-filter, .checklist-create',
             element
        ).toggleAttr('disabled', disabled);

        if (this._controller) {
            this._controller.renderer().disabled(disabled);
            this._controller.redraw();
        }

        return this;
    },

    content: function(element) {
        var content = $('.checklist-content', element);
        return content.length === 0 ? element : content;
    },

    dependencies: function(element) {
        return [];
    },

    reload: function(element, data, cb, error_cb, sync) {
        return this;
    },

    update: function(element, data) {
    },

    model: function(element) {
        return this._controller.model();
    },

    val: function(element, value) {
        var input = this._delegate(element);

        if (value === undefined) {
            return input.val();
        }

        var previous = this.val(element);
        var selections = creme.utils.JSON.clean(value, []);

        value = selections.map(function(item) {
            return Object.isString(item) ? item : JSON.stringify(item);
        });

        if (previous === value) {
            return this;
        }

        if (input) {
            input.val(value).trigger('change');
        }

        element.trigger('change');
        return this;
    },

    cleanedval: function(element) {
        return this.val(element).map(function(value) {
            return creme.utils.convert(value, {
                from: 'string',
                to: this.options.datatype.toLowerCase(),
                defaults: value
            });
        });
    },

    _createItem: function(element, link) {
        if (this._disabled) {
            return this;
        }

        var action = new creme.dialog.FormDialogAction();
        var model = this._model;

        action.onDone(function(event, data) {
                          var choices = creme.model.ChoiceGroupRenderer.choicesFromTuples(data.data().added || []);

                          model.patch({
                              add: choices
                          });
                      })
              .start({
                  url: link.attr('href'),
                  title: link.attr('title')
               });
    },

    reset: function(element) {
        return this.unselectAll(element);
    },

    selected: function(element) {
        return this._selections.selected().map(function(item) {
            return item.value;
        });
    },

    selectAll: function(element) {
        if (!this._disabled) {
            this._selections.selectAll();
        }

        return this;
    },

    unselectAll: function(element) {
        if (!this._disabled) {
            this._selections.unselectAll();
        }

        return this;
    }
});

}(jQuery));
