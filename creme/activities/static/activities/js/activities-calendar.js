/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2024  Hybird

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

creme.FullActivityCalendar = creme.component.Component.sub({
    _init_: function(element, options) {
        options = Object.assign({
            debounceDelay: 200,
            defaultView: 'month',
            keepState: false,
            showWeekNumber: true,
            showTimezoneInfo: false,
            allowEventMove: true,
            fullCalendarOptions: {},
            spanMode: false
        }, options || {});

        this._element = element;
        this._props = options;

        this.debounceDelay(options.debounceDelay);
        this.owner(options.owner || '');
        this.defaultView(options.defaultView);

        /* TODO : check already bound */
        this._bindFilterInputs(element, '.floating-event-filter input', this._filterCalendarEvents.bind(this));
        this._bindFilterInputs(element, '.calendar-menu-filter input', this._filterCalendars.bind(this));

        this._setupCalendarUi(element, options);
        this._setupCalendarToggle(element);
    },

    debounceDelay: function(delay) {
        return Object.property(this, '_debounceDelay', delay);
    },

    owner: function(owner) {
        return Object.property(this, '_owner', owner);
    },

    defaultView: function(view) {
        return Object.property(this, '_defaultView', view);
    },

    element: function() {
        return this._element;
    },

    calendar: function() {
        return this._calendar;
    },

    calendarElement: function() {
        return this._element.find('.calendar');
    },

    _loadStateFromUrl: function(url) {
        var hash = creme.ajax.parseUrl(url || window.location.href).hash || '';
        var data = creme.ajax.decodeSearchData(hash.slice(1));
        var view = data.view && (data.view in this.fullCalendarSettings().views) ? data.view : this.defaultView();
        var date = data.date ? moment(data.date) : undefined;
        date = date && date.isValid() ? date : undefined;

        return {view: view, date: date};
    },

    _storeStateInUrl: function(state) {
        creme.history.push('#' + creme.ajax.param({
            view: state.view,
            date: state.date.format('YYYY-MM-DD')
        }));
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

    _onCalendarStateUpdate: function(calendar, info) {
        this._storeStateInUrl({
            view: info.view, date: info.start
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

    _resizeSidebar: function() {
        var calendar = this._element.find('.calendar');
        var calendarHeight = calendar.height();

        var sidebar = this._element.find('.calendar-menu');
        var sidebarMargin = parseInt(sidebar.css('margin-top'));

        sidebar.css('height', (calendarHeight - sidebarMargin) + 'px');
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
            var id = $(this).val();
            var state = $(this).prop('checked');

            if (state) {
                self.calendar().selectSourceIds([id]);
            } else {
                self.calendar().unselectSourceIds([id]);
            }
        }));
    },

    _floatingEventItemData: function(item) {
        var color = item.data('color');

        return {
            id: item.data('id'),
            title: (item.text() || '').trim(),
            extendedProps: {
                type: item.data('type'),
                user: this.owner(),
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

    _selectedSourceIds: function(element) {
        return this._element.find('input[type="checkbox"][name="calendar_id"]:checked').map(function() {
            return $(this).val();
        }).get();
    },

    _setupCalendarUi: function(element, options) {
        var self = this;
        var state = this._loadStateFromUrl();

        options = Object.assign(options, {
            initialDate: state.date || options.initialDate,
            initialView: state.view || options.initialView,
            externalEventItemData: this._floatingEventItemData.bind(this),
            externalEventContainer: element.find('.floating-activities'),
            externalEventItemSelector: '.floating-event',
            selectedSourceIds: this._selectedSourceIds.bind(this)
        });

        var calendar = this._calendar = new creme.ActivityCalendar(this.calendarElement(), options);
        calendar.on('event-new', this._onCalendarEventCreate.bind(this));
        calendar.on('state-update', this._onCalendarStateUpdate.bind(this));
        calendar.on('query-complete', function() {
            self._resizeSidebar();
        });

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

}(jQuery));
