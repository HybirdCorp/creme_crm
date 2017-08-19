/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2016-2017  Hybird

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

(function($) {"use strict";

creme.jobs = {};

creme.jobs.decorateJobStatus = function(brick_elt, job_id, status, ack_errors) {
    var must_reload = false;
    var ack_errors_label = '';

    if (ack_errors) {
        must_reload = true;

        brick_elt.find('[data-job-ack-errors][data-job-id=' + job_id + ']').each(function(i, e) {
            var elt = $(e);

            if (!elt.find('.ack-errors').length) {
                elt.append('<span class="ack-errors">' +
                           gettext('Communication error with the job manager (last changes have not been taken into consideration)') +
                           '</span>'
                          );
            }
        });
    } else {
        brick_elt.find('[data-job-ack-errors][data-job-id=' + job_id + '] .ack-errors').remove();
    }

    switch(status) {
      case 1: // STATUS_WAIT
        must_reload = true;

        brick_elt.find('[data-job-status][data-job-id=' + job_id + ']').each(function(i, e) {
            var elt = $(e);

            if (!elt.find('.progress').length) {
                elt.append('<img class="progress" src="' + creme_media_url("images/wait.gif") + '" />');
            }
        });

        break;

      case 10: // STATUS_ERROR
        brick_elt.find('[data-job-status][data-job-id=' + job_id + ']').text(gettext('Error')).attr('data-job-status', 10);
        break;

      case 20: // STATUS_OK
        brick_elt.find('[data-job-status][data-job-id=' + job_id + ']').text(gettext('Finished')).attr('data-job-status', 20);
        break;
    }

    return must_reload;
};

creme.jobs.checkJobManager = function(url, brick_id, reload_page) {
    var brick_elt = $('#' + brick_id);  // We retrieve the brick by its ID at each call, because the brick can be reloaded (& so, replaced)
    var job_ids = [];

    brick_elt.find('[data-job-id][data-job-status][data-job-ack-errors]').each(function(i, e) {
        var job_id = e.getAttribute('data-job-id');

        if (creme.jobs.decorateJobStatus(brick_elt, job_id,
                                         Number(e.getAttribute('data-job-status')),
                                         Number(e.getAttribute('data-job-ack-errors'))
                                        )) {
            job_ids.push(job_id);
        }
    });

    if (job_ids.length) {
        url = url + '?' + $.param({'id': job_ids});
    }

    $.ajax({url: url,
            dataType: 'json',
            error: function(request, status, error) {
                var error_panel = brick_elt.find('.global-error');
                error_panel.css('display', '');
                error_panel.text(gettext('HTTP server error'));
            },
            success: function(data, status) {
                var alright = true;  // No error, all jobs are finished.

                var error_panel = brick_elt.find('.global-error');
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

                    if (!Object.isString(job_info) && creme.jobs.decorateJobStatus(brick_elt, job_id, job_info['status'], job_info['ack_errors'])) {
                        alright = false;
                    }
                });

                if (!alright) {
                    setTimeout(creme.jobs.checkJobManager, 5000, url, brick_id, reload_page);
                } else if (reload_page) {
                    window.location = window.location;
                }
            }
    });
};
}(jQuery));
