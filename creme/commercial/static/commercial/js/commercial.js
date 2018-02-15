/*******************************************************************************
    Creme is a free/open-source Customer Relationship Management software
    Copyright (C) 2009-2018  Hybird

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

creme.commercial = creme.commercial || {};

//creme.commercial.postScore = function(url, model_id, segment_desc_id, orga_id, select, reload_url) {
//    console.warn('creme.commercial.postScore() is deprecated (use setScore() & bricks actions instead).');
//
//    var data = {
//            score:           $(select).val(),
//            model_id:        model_id,
//            segment_desc_id: segment_desc_id,
//            orga_id:         orga_id
//        };
//
//    creme.blocks.ajaxPOSTQuery(url, {blockReloadUrl: reload_url}, data).start();
//}

creme.commercial.setScore = function(select_input, url, scored_instance_id, segment_desc_id, orga_id) {
    var $select = $(select_input);
    var brick = $select.parents('.brick').creme().widget().brick();
    var data = {
            score:           $select.val(),
            model_id:        scored_instance_id,
            segment_desc_id: segment_desc_id,
            orga_id:         orga_id
        };

    creme.utils.ajaxQuery(url, {action: 'post', warnOnFail: true}, data)
               .onDone(function() {brick.refresh();})
               .start();
}

//creme.commercial.postCategory = function(url, segment_desc_id, orga_id, select, reload_url) {
//    console.warn('creme.commercial.postCategory() is deprecated (use bricks actions instead).');
//
//    var data = {
//            category:        $(select).val(),
//            segment_desc_id: segment_desc_id,
//            orga_id:         orga_id
//        };
//
//    creme.blocks.ajaxPOSTQuery(url, {blockReloadUrl: reload_url}, data).start();
//}

//creme.commercial.increaseObjectiveCounter = function(url, inc, reload_url) {
//    console.warn('creme.commercial.increaseObjectiveCounter() is deprecated (use bricks actions instead).');
//
//    creme.blocks.ajaxPOSTQuery(url,
//                               {blockReloadUrl: reload_url},
//                               {diff: inc})
//                .start();
//}

}(jQuery));
