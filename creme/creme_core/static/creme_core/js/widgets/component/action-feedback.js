/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2020  Hybird

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
 * Requires : creme.utils
 */

(function($) {
"use strict";

creme.action.FeedbackActionBuilderRegistry = creme.action.DefaultActionBuilderRegistry.sub({
    _build_redirect: function(url, options, data) {
        return this._redirectAction(url, options, data);
    },

    _build_reload: function(url, options, data) {
        return this._reloadAction(url, options, data);
    }
});

creme.action.FeedbackAction = creme.component.Action.sub({
    _init_: function(feedbacks, options) {
        options = $.extend({
            builders: new creme.action.FeedbackActionBuilderRegistry()
        }, options || {});

        feedbacks = feedbacks || [];
        feedbacks = Array.isArray(feedbacks) ? feedbacks : [feedbacks];

        this._feedbacks = feedbacks;
        this._super_(creme.component.Action, '_init_', this._run, options);
    },

    _run: function(options) {
        options = $.extend({}, this._options, options || {});

        var builders = options.builders;
        var feedbacks = this._feedbacks;
        var firstAction, lastAction;
        var self = this;

        if (Object.isEmpty(feedbacks)) {
            return this.done();
        }

        for (var index in feedbacks) {
            var feedback = feedbacks[index];

            try {
                var builder = builders.get(feedback.command);
                var data = feedback.data || {};

                if (Object.isFunc(builder)) {
                    var nextAction = builder(data.url, {}, data);

                    if (Object.isNone(firstAction)) {
                        firstAction = lastAction = nextAction;
                    } else {
                        nextAction.after(lastAction);
                        lastAction = nextAction;
                    }
                } else {
                    console.warn('Unknown feedback action', feedback);
                    return self.fail(feedback);
                }
            } catch (e) {
                console.warn('Invalid feedback action', feedback, e);
                return self.fail(feedback, e);
            }
        }

        this.delegate(lastAction);
        firstAction.start();
    }
});

}(jQuery));
