/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2025  Hybird

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

creme.widget.Toggle = creme.widget.declare('ui-creme-toggle', {
    _create: function(element, options, cb, sync, attributes) {
        options = Object.assign({
            debounceDelay: 200
        }, options || {});

        var self = this;
        var handler = this._onToggle.bind(this);
        var triggers = this.triggers(element);

        if (options.debounceDelay > 0) {
            handler = _.debounce(handler, options.debounceDelay, false);
        }

        this._element = element;
        this._handler = handler;

        triggers.each(function() {
            self._toggleTargets($(this), $(this).hasClass('toggle-collapsed'));
        });

        element.on('click', '[data-toggle]', handler);

        if (element.is('[data-toggle]')) {
            element.on('click', handler);
        }

        element.addClass('widget-ready');
    },

    _destroy: function(element) {
        element.off('click', this._handler);
        element.off('click', '[data-toggle]', this._handler);
    },

    _toggleTargets: function(trigger, state) {
        var targetRef = trigger.data('toggle') || '';
        var targets = [];

        if (targetRef.length > 0) {
            targets = this._element.find(targetRef);
            targets = targets.length > 0 ? targets : $(targetRef);
        }

        trigger.toggleClass('toggle-collapsed', state);
        state = trigger.hasClass('toggle-collapsed');

        if (targets.length > 0) {
            targets.toggleClass('toggle-collapsed', state);
        }

        return targets;
    },

    _onToggle: function(e) {
        var targets = this._toggleTargets($(e.target).closest('[data-toggle]'));

        if (targets.length > 0) {
            e.preventDefault();
        }
    },

    expandAll: function(element) {
        var self = this;
        this.triggers(element).each(function() {
            self._toggleTargets($(this), false);
        });
    },

    collapseAll: function(element) {
        var self = this;
        this.triggers(element).each(function() {
            self._toggleTargets($(this), true);
        });
    },

    triggers: function(element) {
        var triggers =  element.find('[data-toggle]').filter(function() {
            return $(this).parents('.ui-creme-toggle').first().is(element);
        });

        return element.is('[data-toggle]') ? triggers.add(element) : triggers;
    }
});

}(jQuery));
