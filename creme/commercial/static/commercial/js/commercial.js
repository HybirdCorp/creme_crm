/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2014  Hybird

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


creme.commercial = creme.commercial || {};

creme.commercial.postScore = function(url, model_id, segment_desc_id, orga_id, select, reload_url) {
    var data = {
            score:           $(select).val(),
            model_id:        model_id,
            segment_desc_id: segment_desc_id,
            orga_id:         orga_id
        };

    creme.blocks.ajaxPOSTQuery(url, {blockReloadUrl: reload_url}, data).start();
/*
    creme.ajax.post({
                'url': url,
                'data': {
                        //'score':           $(select).find('[selected="true"]').attr("value"),
                        'score':           $(select).val(),
                        'model_id':        model_id,
                        'segment_desc_id': segment_desc_id,
                        'orga_id':         orga_id
                    },
                'success': function(data, status) {
                      creme.blocks.reload(reload_url);
                    }
            });
*/
}

creme.commercial.postCategory = function(url, segment_desc_id, orga_id, select, reload_url) {
    var data = {
            category:        $(select).val(),
            segment_desc_id: segment_desc_id,
            orga_id:         orga_id
        };

    creme.blocks.ajaxPOSTQuery(url, {blockReloadUrl: reload_url}, data).start();
/*
    creme.ajax.post({
                'url': url,
                'data': {
                        //'category':        $(select).find('[selected="true"]').attr("value"),
                        'category':        $(select).val(),
                        'segment_desc_id': segment_desc_id,
                        'orga_id':         orga_id
                    },
                'success': function(data, status) {
                      creme.blocks.reload(reload_url);
                    }
            });
*/
}

creme.commercial.increaseObjectiveCounter = function(objective_id, inc, reload_url) {
    creme.blocks.ajaxPOSTQuery('/commercial/objective/%s/incr'.format(objective_id),
                               {blockReloadUrl: reload_url},
                               {diff: inc})
                .start();
}

/*
creme.commercial.incr_counter = function(diff, url, reload_url) {
    creme.ajax.post({
                'url': url,
                'data': {
                        'diff': diff,
                    },
                'success': function(data, status) {
                      creme.blocks.reload(reload_url);
                    }
            });
}
*/
