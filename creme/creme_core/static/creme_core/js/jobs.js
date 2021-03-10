/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2016-2021  Hybird

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

creme.jobs.BaseJobsMonitor = creme.component.Component.sub({
    _init_: function(url) {
        this._url = url;  // URL for jobs information
        this._onAllJobsFinishedCallBack = function() {};
    },

    decorate: function(element, job_id, status, ack_errors, progress) {
        var must_reload = false;

        if (ack_errors) {
            must_reload = true;

            element.find('[data-job-ack-errors][data-job-id=' + job_id + ']').each(function(i, e) {
                var elt = $(e);

                if (!elt.find('.ack-errors').length) {
                    elt.append('<span class="ack-errors">' +
                               gettext('Communication error with the job manager (last changes have not been taken into consideration)') +
                               '</span>'
                              );
                }
            });
        } else {
            element.find('[data-job-ack-errors][data-job-id=' + job_id + '] .ack-errors').remove();
        }

        switch (status) {
          case 1: // STATUS_WAIT
            must_reload = true;

            if (progress) {
                element.find('[data-job-status][data-job-id=' + job_id + ']').each(function(i, e) {
                    var elt = $(e);
                    var label = progress.label;
                    var percentage = progress.percentage;

                    if (label) {
                        elt.find('.job-progress-bar-label').text(label);
                    } else if (percentage !== null) {
                        elt.find('.job-progress-percentage-value').text(percentage);
                    }

                    if (percentage !== null) {
                        elt.find('progress.job-progress-bar').prop('value', percentage);
                    }
                });
            }

            break;

          case 10: // STATUS_ERROR
            element.find('[data-job-status][data-job-id=' + job_id + ']').text(gettext('Error')).attr('data-job-status', 10);
            break;

          case 20: // STATUS_OK
            element.find('[data-job-status][data-job-id=' + job_id + ']').text(gettext('Finished')).attr('data-job-status', 20);
            break;
        }

        return must_reload;
    },

    get_element: function() {
        throw Error('Not implemented !');
    },

    onAllJobsFinished: function(callback) {
        this._onAllJobsFinishedCallBack = callback;

        return this;
    },

    start: function() {
        var monitor = this;

        function _process() {
            var element = monitor.get_element();
            var job_ids = [];

            element.find('[data-job-id][data-job-status][data-job-ack-errors]').each(function(i, e) {
                var job_id = e.getAttribute('data-job-id');

                if (monitor.decorate(element, job_id,
                                     Number(e.getAttribute('data-job-status')),
                                     Number(e.getAttribute('data-job-ack-errors')),
                                     null
                                    )) {
                    job_ids.push(job_id);
                }
            });

            var uri = monitor._url;
            if (job_ids.length) {
                uri += '?' + creme.ajax.param({'id': job_ids}, true);
            }

            $.ajax({url: uri,
                    dataType: 'json',
                    error: function(request, status, error) {
                        var error_panel = element.find('.global-error');
                        error_panel.css('display', '');
                        error_panel.text(gettext('HTTP server error'));
                    },
                    success: function(data, status) {
                        var alright = true;  // No error, all jobs are finished.

                        var error_panel = element.find('.global-error');
                        var error = data['error'];
                        if (error !== undefined) {
                            error_panel.css('display', '');
                            error_panel.text(error);

                            alright = false;
                        } else {
                            error_panel.css('display', 'none');
                        }

                        job_ids.forEach(function (job_id, index, array) {
                            var job_info = data[job_id];

                            if (Object.isString(job_info)) {
                                console.log('Server returned an error for job <', job_id, '> => ', job_info);
                                return;
                            }

                            if (Object.isNone(job_info)) {
                                console.log('Invalid data for job <', job_id, '> => ', job_info);
                                return;
                            }

                            if (monitor.decorate(element, job_id, job_info['status'], job_info['ack_errors'], job_info['progress'])) {
                                alright = false;
                            }
                        });

                        if (!alright) {
                            setTimeout(_process, 5000);
                        } else {
                            monitor._onAllJobsFinishedCallBack();
                        }
                    }
            });
        }

        _process();
    }
});

creme.jobs.JobsMonitor = creme.jobs.BaseJobsMonitor.sub({
    _init_: function(url, element) {
        this._super_(creme.jobs.BaseJobsMonitor, '_init_', url);
        this._element = element;
    },

    get_element: function() {
        return this._element;
    }
});

creme.jobs.BrickJobsMonitor = creme.jobs.BaseJobsMonitor.sub({
    _init_: function(url, brick_id) {
        this._super_(creme.jobs.BaseJobsMonitor, '_init_', url);
        this._brick_id = brick_id;
    },

    get_element: function() {
        // We retrieve the brick by its ID at each call, because the brick can be reloaded (& so, replaced)
        return $('#' + this._brick_id);
    }
});


creme.jobs.PopupJobWaitingController = creme.widget.declare('job-waiting-ctrl', {
    _create: function(element, options, cb, sync, args) {
        var dialog = element.parents('.ui-dialog:first');
        var buttons = dialog.find('.ui-dialog-buttonset');

        var close_button = buttons.find('[name="cancel"]');
        // TODO: improve buttons API to set it from HTML ??
        close_button.find('.ui-button-text').text(gettext('Close (process in background)'));

        var terminate_button = buttons.find('[name="send"]');
        terminate_button.hide();

        element.addClass('widget-ready');

        new creme.jobs.JobsMonitor(element.attr('data-jobs-info-url'), element)
                      .onAllJobsFinished(function() {
                          close_button.hide();
                          terminate_button.show();
                      })
                      .start();
    },

    _destroy: function(element) {}
});

}(jQuery));
