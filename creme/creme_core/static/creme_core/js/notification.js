/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2024-2025  Hybird

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
 * Requires : jQuery
 *            creme
 */

(function($) {
"use strict";

creme.notification = {};

/* globals clearInterval setInterval creme_media_url */
creme.notification.NotificationBox = creme.component.Component.sub({
    _init_: function(element, options) {
        options = Object.assign({
            refreshDelay: 300000,      // In milliseconds. Default 5 minutes.
            deltaRefreshDelay: 60000,  // In milliseconds. Default 1 minutes.
            refreshUrl: '',
            discardUrl: ''
        }, options || {});

        Assert.not(Object.isEmpty(options.refreshUrl), 'refreshUrl is required');
        Assert.not(Object.isEmpty(options.discardUrl), 'discardUrl is required');

        Assert.not(element.is('.is-active'), 'NotificationBox is already active');

        this._element = element;
        this._refreshDelay = options.refreshDelay;
        this._deltaRefreshDelay = options.deltaRefreshDelay;
        this._initialDataSelector = options.initialDataSelector;
        this._refreshUrl = options.refreshUrl;
        this._discardUrl = options.discardUrl;

        this.setup(element, options);
    },

    isFetchActive: function() {
        return Boolean(this._fetchJob);
    },

    isPaused: function() {
        return document.hidden;
    },

    initialData: function() {
        var script = this._element.find('script[type$="/json"].notification-box-data:first');
        var data = _.readJSONScriptText(script.get(0));

        return Object.assign({
            count: 0,
            notifications: []
        }, Object.isEmpty(data) ? {} : JSON.parse(data));
    },

    setup: function(element, options) {
        var self = this;

        this._count = 0;
        this._overlay = new creme.dialog.Overlay();

        this._updateBox(this.initialData());

        // NB: we attach to <ul> & not the parent <div> because the overlay sets
        //     the position as "relative" (which breaks our layout).
        //     It's even better because by doing this way the overlay does not
        //     hide the link "See all notifications".
        this._overlay.bind($('.notification-items', element))
                     .addClass('notification-loading')
                     .content(
                        '<h2><img src="${src}"><span>${label}</span></h2>'.template({
                            src: creme_media_url('images/wait.gif'),
                            label: gettext('Loading…')
                        })
                     );

        element.on('click', '.discard-notification', function(e) {
            e.preventDefault();
            self._onDiscardItem($(this).parents('.notification-item:first'));
        });

        this.startFetch();
        element.addClass('is-active');

        return this;
    },

    startFetch: function() {
        if (!this.isFetchActive()) {
            this._fetchJob = setInterval(this._fetchItems.bind(this), this._refreshDelay);
            this._timeDeltaJob = setInterval(this._updateDeltas.bind(this), this._deltaRefreshDelay);
        }

        return this;
    },

    stopFetch: function() {
        if (!Object.isNone(this._fetchJob)) {
            clearInterval(this._fetchJob);
            this._fetchJob = null;
        }

        if (!Object.isNone(this._timeDeltaJob)) {
            clearInterval(this._timeDeltaJob);
            this._timeDeltaJob = null;
        }

        return this;
    },

    _onDiscardItem: function(item) {
        var self = this;
        var id = item.data('id');

        if (!Object.isEmpty(id)) {
            creme.utils.ajaxQuery(
                this._discardUrl,
                {action: 'post', warnOnFail: true},
                {id: id}
            ).onDone(function() {
                item.remove();
                self._updateCounter(self._count - 1);
            }).start();
        }
    },

    _humanizedTimeDelta: function(secondsTimedelta) {
        // TODO: use momentjs for this job
        var minutesTimeDelta = Math.floor(secondsTimedelta / 60);

        if (minutesTimeDelta < 1) {
            return gettext('A few moments ago');
        } else if (minutesTimeDelta < 60) {
            return ngettext(
                '%d minute ago', '%d minutes ago', minutesTimeDelta
            ).format(minutesTimeDelta);
        }

        var hoursTimeDelta = Math.floor(minutesTimeDelta / 60);

        if (hoursTimeDelta < 24) {
            return ngettext(
                'More than %d hour ago', 'More than %d hours ago', hoursTimeDelta
            ).format(hoursTimeDelta);
        }

        var daysDelta = Math.floor(hoursTimeDelta / 24);
        return ngettext(
            'More than %d day ago', 'More than %d days ago', daysDelta
        ).format(daysDelta);
    },

    _updateCounter: function(count) {
        this._count = count;
        var countWidget = this._element.find('.notification-box-count');
        countWidget.text(count);
        countWidget.toggleClass('is-empty', !count);
    },

    _updateDeltas: function() {
        if (this.isPaused()) {
            return;
        }

        var self = this;
        var now = Date.now();

        $('.notification-item').each(function() {
            var item = $(this);
            var created = parseInt(item.data('created'));
            var label = self._humanizedTimeDelta(Math.round((now - created) / 1000));

            item.find('.notification-created').text(label);
        });
    },

    _updateItems: function(notifications) {
        var element = this._element;
        var items = element.find('.notification-items');

        var now = Date.now();

        var html = notifications.map(function(itemData) {
            var created = Date.parse(itemData.created);
            var createdLabel = new Date(created).toLocaleString();

            return (
                '<li class="notification-item notification-item-level${level}" data-id="${id}" data-created="${created}">' +
                    '<span class="notification-channel">${channel}</span>' +
                    '<span class="notification-subject">${subject}</span>' +
                    '<span class="notification-created" title="${createdLabel}">${timeDeltaLabel}</span>' +
                    '<div class="notification-body">${body}</div>' +
                    '<button type="button" class="discard-notification">${discardLabel}</button>' +
                '</li>'
            ).template({
                id: itemData.id,
                level: itemData.level,
                channel: itemData.channel,
                created: created,
                createdLabel: createdLabel,
                timeDeltaLabel: this._humanizedTimeDelta(Math.round((now - created) / 1000)),
                subject: itemData.subject,
                body: itemData.body,
                discardLabel: gettext('Validate')
            });
        }.bind(this)).join('');

        items.html(html);
    },

    _updateBox: function(data) {
        this._updateCounter(data.count);
        this._updateItems(data.notifications);
    },

    _updateErrorMessage: function(message) {
        var container = this._element.find('.notification-error');
        container.toggleClass('is-empty', message === undefined || message === '');
        container.find('span').text(message || '');
    },

    _fetchItems: function() {
        /*
          Skips the fetching if the window/tab is not visible, so we avoid to flood the server
          when there are many Creme tabs.

          NOTE :
          The 'visibilitychange' seems a good idea BUT "dangerous" because it appears many times even without any need and
          can mess up the state of the timeout loop.
          So keeping the loop and ignoring a fetch each 5 minutes is way more simpler and efficient.
        */
        if (this.isPaused()) {
            return;
        }

        var self = this;
        var overlay = this._overlay;

        overlay.visible(true);

        this._fetchQuery = creme.ajax.query(
            this._refreshUrl, {backend: {sync: false, dataType: 'json'}}
        ).onDone(function(event, data) {
            self._updateBox(data);
            self._updateErrorMessage('');
        }).onFail(function(event, data, error) {
            /* E.g.
             - event === fail
             - data === undefined
             - error === {type: 'request', status: 0, request: {…}, message: 'HTTP 0 - error'}
            */
            self._updateErrorMessage(
                gettext('An error happened when retrieving notifications (%s)').format(error.message)
            );
        }).onComplete(function() {
            overlay.visible(false);
        }).start();
    }
});

creme.setupNotificationBox = function(element, options) {
    /*
      Wrapper function to setup the notification box in a template.
       - Keeps the template javascript as simple as possible.
       - The linter often complains about new Object() without returning them on store in a variable.
       - Allows to add try catch or check if the element exists (e.g : toggle the feature in templates).
    */
    return new creme.notification.NotificationBox($(element), options);
};

}(jQuery));
