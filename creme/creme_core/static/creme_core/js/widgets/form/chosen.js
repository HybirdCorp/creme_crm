/*******************************************************************************
 * Creme is a free/open-source Customer Relationship Management software
 * Copyright (C) 2009-2022 Hybird
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option) any
 * later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 ******************************************************************************/

(function($) {
"use strict";

creme.form = creme.form || {};

creme.form.Chosen = creme.component.Component.sub({
    _init_: function(options) {
        this.options = $.extend({
            multiple: false,
            sortable: false,
            allow_single_deselect: true,
            no_results_text: gettext("No result"),
            placeholder_text_multiple: gettext("Select some options"),
            placeholder_text_single: gettext("Select one option")
        }, options || {});
    },

    isActive: function() {
        return this.chosen !== undefined;
    },

    activate: function(element) {
        if (this.isActive()) {
            throw new Error('Chosen component is already active');
        }

        var options = this.options;
        var chosen = element.addClass('chzn-select').chosen(options);

        if (options.multiple && options.sortable) {
            this._activateSort(element);
        }

        this.chosen = chosen;
        this.element = element;
        return chosen;
    },

    deactivate: function() {
        if (this.isActive() === false) {
            return;
        }

        var choicelist = $('ul.chzn-choices:not(.sortable)', this.element.parent());

        if (this.options.sortable) {
            choicelist.sortable('destroy');
        }

        this.element.unchosen();
        this.element.removeClass('chzn-select chzn-done');

        this.chosen = undefined;
        this.element = undefined;
    },

    refresh: function() {
        this.chosen.trigger("liszt:updated");
    },

    _querychoices: function(element, key) {
        return $('option' + (key ? '[value="' + key + '"]' : ''), element).filter(function() {
            return $(this).parents('select').first().is(element);
        });
    },

    _activateSort: function(element) {
        var self = this;
        var choicelist = $('ul.chzn-choices:not(.sortable)', element.parent());

        choicelist.sortable({
            items:   'li.search-choice',
            opacity: 0.5,
            revert:  200,
            delay:   200,
            update:  function(event, ui) {
                var sorted = [];
                var choices = self._querychoices(element).map(function() {
                    return $(this).attr('value');
                });

                $('li.search-choice a.search-choice-close', choicelist).each(function() {
                    var index = -1;
                    try {
                        index = parseInt($(this).attr('rel'));
                    } catch (e) {
                    }

                    if (index > -1 && index < choices.length) {
                        sorted.push(choices[index]);
                    }
                });

                element.attr('sorted', sorted.join(','));
            }
        });

        choicelist.addClass('sortable').disableSelection();
    }
});
}(jQuery));
