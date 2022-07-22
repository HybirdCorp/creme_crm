/*
 * Hacky fix for a bug in select2 with jQuery 3.6.0's new nested-focus "protection"
 * see: https://github.com/select2/select2/issues/5993
 * see: https://github.com/jquery/jquery/issues/4382
 *
 * TODO: Recheck with the select2 GH issue and remove once this is fixed on their side
*/

(function($) {
"use strict";

$(document).on('select2:open', function() {
    var search = document.querySelector('.select2-container--open .select2-search__field');

    if (search) {
        setTimeout(function() {
            search.focus();
        }, 100);
    }
});

}(jQuery));
