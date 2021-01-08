
(function($) {
    "use strict";

    function buildButtonChoice(choice) {
        return $((
            '<span class="menu_button" title="${description}">' +
                '${label}<input type="hidden" name="${name}" value="${value}"/>' +
            '</span>'
        ).template(choice)).prop("disabled", !choice.selected);
    }

    function buildWidget(widget, choices) {
        choices.forEach(
            function (choice) {
                if (choice.selected) {
                    widget.find(".widget-selected .widget-container").append(
                        buildButtonChoice(choice)
                    );
                } else {
                    widget.find(".widget-available .widget-container").append(
                        buildButtonChoice(choice)
                    );
                }
            }
        );
    }

    creme.initButtonMenuWidget = function (widget, options) {
        var buttonsWidgetOptgroups = JSON.parse(document.getElementById(options.optionsId).textContent);

        buildWidget(widget, buttonsWidgetOptgroups);

        function onSortEventHandler(event) {
            widget.find(".widget-available input").prop("disabled", true);
            widget.find(".widget-selected input").prop("disabled", false);
        }

        var groupName = widget.attr("id");

        new Sortable(  // eslint-disable-line
            widget.find(".widget-available .widget-container").get(0),
            {
            group: groupName,
            animation: 150,
            sort: false,
            onSort: onSortEventHandler
        });

        new Sortable(  // eslint-disable-line
            widget.find(".widget-selected .widget-container").get(0),
            {
            group: groupName,
            animation: 150,
            onSort: onSortEventHandler
        });
    };
}(jQuery));
