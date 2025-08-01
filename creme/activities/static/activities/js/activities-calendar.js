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

creme.ActivityCalendarController = creme.component.Component.sub({
    _init_: function(element, options) {
        this._props = options = Object.assign({
            allowEventMove: true,
            allowEventOverlaps: true,
            debounceDelay: 200,
            defaultView: 'month',
            fullCalendarOptions: {},
            keepState: false,
            showWeekNumber: true,
            showTimezoneInfo: false,
            timezoneOffset: 0,
            sourceSelectUrl: ''
        }, options || {});

        this._element = element;
        this._fullCalendarViewNames = creme.availableFullCalendarViewNames(options);

        Assert.not(element.is('.is-active'), 'creme.ActivityCalendarController is already bound');

        this._bindFilterInputs(element, '.floating-event-filter input', this._filterCalendarEvents.bind(this));
        this._bindFilterInputs(element, '.calendar-menu-filter input', this._filterCalendars.bind(this));

        this._setupCalendarUi(element, options);
        this._setupCalendarToggle(element);
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

    fullCalendarViewNames: function() {
        return this._fullCalendarViewNames;
    },

    debounceDelay: function(delay) {
        return this.prop('debounceDelay', delay);
    },

    calendar: function() {
        return this._calendar;
    },

    element: function() {
        return this._element;
    },

    keepState: function(keep) {
        return this.prop('keepState', keep);
    },

    sourceSelectUrl: function(url) {
        return this.prop('sourceSelectUrl', url);
    },

    selectedSourceIds: function() {
        return this._calendar.selectedSourceIds();
    },

    selectSource: function(ids) {
        var next = new Set(ids || []);

        if (this.sourceSelectUrl()) {
            var prev = new Set(this.selectedSourceIds());

            var added = _.reject(Array.from(next), function(id) { return prev.has(id); });
            var removed = _.reject(Array.from(prev), function(id) { return next.has(id); });
            var data = {};

            if (added.length > 0) {
                data.add = added;
            }

            if (removed.length > 0) {
                data.remove = removed;
            }

            if (added.length > 0 || removed.length > 0) {
                creme.ajax.query(this.sourceSelectUrl(), {action: 'POST'}, data).start();
            }
        }

        this._calendar.selectedSourceIds(next);
        return this;
    },

    fullCalendar: function() {
        return this._calendar.fullCalendar();
    },

    fullCalendarView: function(view, options) {
        return this._calendar.fullCalendarView(view, options);
    },

    fullCalendarEvents: function() {
        return this._calendar.fullCalendarEvents();
    },

    setViewState: function(state) {
        this._calendar.fullCalendarView(
            state.view,
            state.date ? state.date.format('YYYY-MM-DD') : undefined
        );

        return this;
    },

    goToDate: function(date) {
        this.calendar().goToDate(date);
    },

    _onCalendarEventCreate: function(event, info) {
        if (info.external) {
            var group = info.item.parents('.menu-group').first();
            info.item.detach();

            group.toggleClass('is-empty-group', group.find('.floating-event').length === 0);
        } else {
            if (info.redirectUrl) {
               creme.utils.goTo(info.redirectUrl);
            } else {
                info.activityCalendar.refetchEvents();
            }
        }
    },

    _currentUrl: function() {
        return window.location.href;
    },

    _loadStateFromUrl: function(url) {
        var hash = _.urlAsDict(url || this._currentUrl()).hash || '';
        var data = _.decodeURLSearchData(hash.slice(1));
        var view = data.view && (this.fullCalendarViewNames().indexOf(data.view) !== -1 ? data.view : this.prop('defaultView'));
        var date = data.date ? moment(data.date) : undefined;
        date = date && date.isValid() ? date : undefined;

        return {view: view, date: date};
    },

    _storeStateInUrl: function(state) {
        creme.history.push('#' + _.encodeURLSearch({
            view: state.view,
            date: state.date.format('YYYY-MM-DD')
        }));
    },

    _onCalendarStateUpdate: function(event, info) {
        if (!this.keepState()) {
            return;
        }

        var previous = (this._loadStateFromUrl() || {});
        var prevDate = previous.date ? previous.date.format('YYYY-MM-DD') : null;
        var nextDate = info.start.format('YYYY-MM-DD');

        if (info.view === previous.view && nextDate === prevDate) {
            return;
        }

        /*
         * In month view the activeStart & activeEnd are enclosing the stored date.
         * Do not change the state if the date is still within view range.
         */
        if (info.view === 'month' && previous.date && previous.date.isBetween(info.start, info.end)) {
            return;
        }

        this._storeStateInUrl({
            view: info.view,
            date: info.start
        });
    },

    _debounce: function(handler) {
        var delay = this.debounceDelay();

        if (delay > 0) {
            return _.debounce(handler, delay);
        } else {
            return handler;
        }
    },

    _filterCalendars: function(element, search) {
        element.find('.other-calendars .calendar-menu-usergroup').each(function() {
            var username = $(this).attr('data-user');
            var calendars = $(this).find('.calendar-menu-item');
            var title = $(this).find('.calendar-menu-usergroup-label');

            var isOwnerMatches = (
               username.toUpperCase().indexOf(search) !== -1 ||
               title.text().toUpperCase().indexOf(search) !== -1
            );

            if (isOwnerMatches) {
                title.removeClass('hidden');
                calendars.removeClass('hidden');
            } else {
                var anyCalendarMatch = false;

                calendars.each(function() {
                    var match = $(this).find('label').text().toUpperCase().indexOf(search) !== -1;
                    $(this).toggleClass('hidden', !match);
                    anyCalendarMatch |= match;
                });

                title.toggleClass('hidden', !anyCalendarMatch);
            }
        });
    },

    _filterCalendarEvents: function(element, search) {
        element.find('.floating-event').each(function() {
            $(this).toggleClass('hidden', $(this).text().toUpperCase().indexOf(search) === -1);
        });
    },

    _bindFilterInputs: function(element, query, callback) {
        element.on('propertychange keyup input paste', query, this._debounce(function(e) {
            callback(element, $(this).val().toUpperCase());
        }));
    },

    _setupCalendarToggle: function(element) {
        var self = this;

        element.on('change', '.calendar-menu-item input[type="checkbox"]', this._debounce(function(e) {
            self.selectSource(self.checkedSourceIds());
        }));
    },

    _externalEventData: function(item) {
        var color = item.data('color');

        return {
            id: item.data('id'),
            title: (item.text() || '').trim(),
            extendedProps: {
                type: item.data('type'),
                user: this.calendar().owner(),
                calendar: item.data('calendar'),
                busy: Boolean(item.data('busy'))
            },
            className: [],
            url: item.data('popup_url'),
            editable: true,
            create: false,
            backgroundColor: color,
            textColor: new RGBColor(color).foreground().toString()
        };
    },

    checkedSourceIds: function(element) {
        return this._element.find('input[type="checkbox"][name="calendar_id"]:checked').map(function() {
            return $(this).val();
        }).get();
    },

    _setupCalendarUi: function(element, options) {
        var self = this;
        var state = self._loadStateFromUrl();
        var initialState = {
            date: options.initialDate ? moment(options.initialDate) : moment(),
            view: options.initialView
        };

        state = {
            date: state.date ? state.date : initialState.date,
            view: state.view ? state.view : initialState.view
        };

        options = Object.assign({}, options, {
            initialDate: state.date,
            initialView: state.view,
            externalEventData: this._externalEventData.bind(this),
            externalEventContainer: element.find('.floating-activities'),
            externalEventItemSelector: '.floating-event',
            selectedSourceIds: this.checkedSourceIds()
        });

        var calendarElement = this._element.find('.calendar');
        var calendar = this._calendar = new creme.ActivityCalendar(calendarElement, options);

        element.addClass('is-active');

        calendar.on('event-new', this._onCalendarEventCreate.bind(this));
        calendar.on('range-select', this._onCalendarStateUpdate.bind(this));

        $(window).on('hashchange', function() {
            if (self.keepState()) {
                var state = self._loadStateFromUrl();

                if (state.view) {
                    calendar.fullCalendarView(
                        state.view,
                        state.date ? state.date.format('YYYY-MM-DD') : undefined
                    );
                }
            }
        });
    }
});

creme.userActivityCalendar = function(element, options) {
    return new creme.ActivityCalendarController(element, options);
};

}(jQuery));
