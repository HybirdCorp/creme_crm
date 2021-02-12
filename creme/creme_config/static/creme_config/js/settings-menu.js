(function($) {
"use strict";

creme.UserSettingController = creme.component.Component.sub({
    _init_: function(element) {
        element.on('change', '.user-setting-toggle', function() {
            var item = $(this);
            var data = {};

            data[item.attr('name')] = item.val();

            creme.ajax.query(item.data('url')).onDone(function() {
                creme.utils.reload();
            }).post(data);
        });
    }
});

}(jQuery));
