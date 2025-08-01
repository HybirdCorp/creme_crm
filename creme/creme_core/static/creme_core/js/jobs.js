/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2016-2025  Hybird

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
 */

(function($) {
"use strict";

creme.jobs = {};

var __JOB_STATUS = {
    WAIT: 1,
    ERROR: 10,
    OK: 20
};

creme.jobs.BaseJobsMonitor = creme.component.Component.sub({
    _init_: function(options) {
        options = $.extend({
            fetchDelay: 5000
        }, options || {});

        this._url = options.url;  // URL for jobs information
        this._fetchDelay = options.fetchDelay;
        this._events = new creme.component.EventHandler();
    },

    on: function(event, listener, decorator) {
        this._events.on(event, listener, decorator);
        return this;
    },

    off: function(event, listener) {
        this._events.off(event, listener);
        return this;
    },

    one: function(event, listener) {
        this._events.one(event, listener);
        return this;
    },

    trigger: function(event, data) {
        this._events.trigger(event, data, this);
        return this;
    },

    _updateErrorState: function(errorMessage) {
        var label = this.element().find('.global-error');

        label.toggleClass('hidden', Object.isEmpty(errorMessage))
             .text(errorMessage);
    },

    _updateJobState: function(jobId, jobState) {
        jobState = jobState || {};

        var needReload = false;
        var jobs = this.jobItems(jobId);
        var progress = jobState.progress || {};

        if (jobState.ack_errors) {
            needReload = true;

            jobs.each(function() {
                var item = $(this);

                if (item.find('.ack-errors').length === 0) {
                    item.append(
                        '<span class="ack-errors">${message}</span>'.template({
                            message: gettext('Communication error with the job manager (last changes have not been taken into consideration)')
                        })
                    );
                }
            });
        } else {
            jobs.find('.ack-errors').remove();
        }

        jobs.attr('data-job-status', jobState.status);
        jobs.data('job-status', jobState.status);

        switch (jobState.status) {
            case __JOB_STATUS.WAIT:
                needReload = true;

                if (progress) {
                    jobs.each(function() {
                        var item = $(this);

                        item.find('.job-progress-bar-label').text(progress.label || '');
                        item.find('.job-progress-percentage-value').text(progress.percentage || '');
                        item.find('progress.job-progress-bar').prop('value', progress.percentage || 0);
                    });
                }
                break;

            case __JOB_STATUS.ERROR:
                jobs.text(gettext('Error'));
                break;

            case __JOB_STATUS.OK: // STATUS_OK
                jobs.text(gettext('Completed successfully'));  // TODO: keep synchronized with python code...
                break;
        }

        return needReload;
    },

    element: function() {
        throw Error('Not implemented !');
    },

    jobItems: function(jobId) {
        return this.element().find('[data-job-id="' + jobId + '"]');
    },

    url: function(url) {
        return Object.property(this, '_url', url);
    },

    fetchDelay: function(state) {
        return Object.property(this, '_fetchDelay', state);
    },

    _retry: function() {
        this._cancelDeferFetch();
        this._deferred = setTimeout(
            this.fetch.bind(this),
            Math.max(100, this.fetchDelay())
        );
    },

    _cancelDeferFetch: function() {
        if (Object.isNone(this._deferred) === false) {
            clearTimeout(this._deferred);
            this._deferred = null;
        }
    },

    fetch: function() {
        var self = this;
        var element = this.element();
        var jobIds = [];

        this._cancelDeferFetch();

        element.find('[data-job-id]').each(function() {
            var jobId = $(this).data('job-id');
            var needReload = self._updateJobState(jobId, {
                status: $(this).data('job-status'),
                ack_errors: $(this).data('job-ack-errors')
            });

            if (needReload) {
                jobIds.push(jobId);
            }
        });

        self.trigger('fetch', jobIds);

        var query = creme.ajax.query(self.url(), {backend: {dataType: 'json'}}, {id: jobIds});

        query.onFail(function() {
            self._updateErrorState(gettext('HTTP server error'));
        }).onDone(function(event, data) {
            var isOk = Object.isEmpty(data.error);  // No error
            var needReload = !isOk;  // with an error we need to relad anyway

            self._updateErrorState(data.error);

            if (isOk) {
                jobIds.forEach(function(jobId, index, array) {
                    var jobState = data[jobId];

                    if (Object.isString(jobState)) {
                        console.log('Server returned an error for job <${job}> → ${state}'.template({
                            job: jobId, state: jobState
                        }));
                    } else if (Object.isNone(jobState)) {
                        console.log('Invalid state for job <${job}>'.template({job: jobId}));
                    } else {
                        needReload |= self._updateJobState(jobId, jobState);
                    }
                });
            }

            if (needReload) {
                self._retry();
            } else {
                self.trigger('finished');
            }
        }).get();
    }
});

creme.jobs.JobsMonitor = creme.jobs.BaseJobsMonitor.sub({
    _init_: function(element, options) {
        this._super_(creme.jobs.BaseJobsMonitor, '_init_', options);
        this._element = element;
    },

    element: function() {
        return this._element;
    }
});

creme.jobs.BrickJobsMonitor = creme.jobs.BaseJobsMonitor.sub({
    _init_: function(brick, options) {
        options = options || {};
        this._super_(creme.jobs.BaseJobsMonitor, '_init_', options);
        this._brickId = brick.id();
    },

    element: function() {
        // We retrieve the brick by its ID at each call, because the brick can be reloaded (& so, replaced)
        return $('#' + this._brickId);
    }
});


creme.jobs.PopupJobWaitingController = creme.widget.declare('job-waiting-ctrl', {
    _create: function(element, options, cb, sync, args) {
        var dialog = element.parents('.ui-dialog').first();
        var buttons = dialog.find('.ui-dialog-buttonset');
        var cancel = buttons.find('.ui-button[name="cancel"]');
        var terminate = buttons.find('.ui-button[name="send"]');

        cancel.text(gettext('Close (process in background)'));
        terminate.hide();

        element.addClass('widget-ready');

        var jobs = new creme.jobs.JobsMonitor(element, {
            url: element.attr('data-jobs-info-url')
        });

        jobs.on('finished', function() {
            cancel.hide();
            terminate.show();
        }).fetch();
    },

    _destroy: function(element) {}
});

}(jQuery));
