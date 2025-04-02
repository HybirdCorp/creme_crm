/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2025  Hybird

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

creme.ActivityCalendarBrickController = creme.component.Component.sub({
    _init_: function(props) {
        this._props = Object.assign({
            fullCalendarOptions: {}
        }, props || {});
    },

    props: function(props) {
        if (props === undefined) {
            return Object.assign({}, this._props);
        }

        this._props = Object.assign(this._props || {}, props);
        return this;
    },

    prop: function(name, value) {
        if (value === undefined) {
            return this._props[name];
        } else {
            this._props[name] = value;
            return this;
        }
    },

    brick: function() {
        return this._brick;
    },

    calendar: function() {
        return this._calendar;
    },

    isBound: function() {
        return !Object.isNone(this._brick);
    },

    _calendarSettings: function(element) {
        var script = $('script[type$="/json"].brick-calendar-settings:first', element);
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? {} : JSON.parse(data);
    },

    _calendarSources: function(element) {
        var script = $('script[type$="/json"].brick-calendar-sources:first', element);
        var data = _.readJSONScriptText(script.get(0));

        return Object.isEmpty(data) ? [] : JSON.parse(data);
    },

    bind: function(brick) {
        Assert.that(Object.isNone(this._brick), 'ActivityCalendarBrickController is already bound');
        Assert.is(brick, creme.bricks.Brick, '${brick} is not a creme.bricks.Brick', {brick: brick});

        this._brick = brick;

        var props = this.props();
        var element = brick.element();
        var container = element.find('.brick-calendar');
        var settings = this._calendarSettings(element);
        var extra = settings.extra_data || {};
        var sources = this._calendarSources(element);

        if (Array.isArray(extra) || _.isString(extra) || _.isNumber(extra)) {
            console.warn('Ignore the extra_data field that must be a plain object :', extra);
            extra = {};
        }

        props = Object.assign({
            selectedSourceIds: sources,
            keepState: Boolean(settings.allow_keep_state),
            defaultView: settings.view || 'month',
            timezoneOffset: settings.utc_offset || 0,
            allowEventMove: Boolean(settings.allow_event_move),
            allowEventCreate: Boolean(settings.allow_event_create),
            headlessMode: Boolean(settings.headless_mode),
            showWeekNumber: !(settings.show_week_number === false),
            showTimezoneInfo: Boolean(settings.show_timezone_info),
            fullCalendarOptions: Object.assign(extra, {
                slotDuration: settings.slot_duration,
                businessHours: {
                    daysOfWeek: settings.week_days,
                    startTime: settings.day_start,
                    endTime: settings.day_end
                },
                firstDay: settings.week_start
            })
        }, props);

        this._calendar = new creme.ActivityCalendar(container, props);
        return this;
    },

    registerActions: function(brick) {
        Assert.is(brick, creme.bricks.Brick, '${brick} is not a creme.bricks.Brick', {brick: brick});
        brick.getActionBuilders().registerAll({});
        return this;
    }
});

creme.setupActivityCalendarBrick = function(element, options) {
    var controller = new creme.ActivityCalendarBrickController(options);

    $(element).on('brick-ready', function(e, brick) {
        controller.bind(brick);
    }).on('brick-setup-actions', function(e, brick, actions) {
        controller.registerActions(brick);
    });

    return controller;
};

}(jQuery));
