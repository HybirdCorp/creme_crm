(function($) {
    "use strict";

    window.QUnitDetailViewMixin = {
        afterEach: function() {
            // detach menu hat bars
            creme.widget.shutdown($('.ui-creme-hatmenubar'));
            $('.ui-creme-hatmenubar').detach();
        },

        createHatMenuBarHtml: function(options) {
            options = $.extend({
                buttons: []
            }, options || {});

            var html = (
                '<div widget="ui-creme-hatmenubar" class="ui-creme-hatmenubar ui-creme-widget">' +
                    '${buttons}' +
                '</div>').template({
                    buttons: (options.buttons || []).join('')
                });

            return html;
        },

        createHatMenuBar: function(options) {
            var html = this.createHatMenuBarHtml(options);

            var element = $(html).appendTo(this.qunitFixture());
            return creme.widget.create(element);
        },

        /* TODO: rename (createActionBarButton?) ? */
        createHatMenuActionButton: function(options) {
            return (
                '<a href="${url}" data-action="${action}" class="menu_button">' +
                    '<script type="application/json"><!-- ${data} --></script>' +
                '</a>').template({
                    url: options.url,
                    action: options.action,
                    data: JSON.stringify({
                        data: options.data || {},
                        options: options.options || {}
                    })
                });
        },

        /* TODO: in brick mixin? */
        createButtonsBrick: function(options) {
            return this.createBrickWidget({
                classes: ['creme_core-buttons-brick'],
                content: (options.buttons || []).join('')
            });
        }
    };

}(jQuery));
