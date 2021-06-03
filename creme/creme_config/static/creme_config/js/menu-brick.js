creme.creme_config = creme.creme_config || {};

creme.creme_config.MenuContainersController = creme.component.Component.sub({
//    _init_: function(options) {
//        this._options = options || {};
//    },

    bind: function(brick) {
        if (this.isBound()) {
            throw new Error('MenuContainersController is already bound');
        }

        var brickElement = brick.element();

        function onSortEventHandler(event) {
            var url = event.item.getAttribute('data-reorderable-menu-container-url');
            if (!url) {
                throw new Error('MenuContainersController: no drag & drop URL found.');
            }

            brick.action('update', url, {}, {target: event.newIndex + 1})
                 .on({
//                     done: function() { console.log('Success'); },
                     fail: function() {
                        console.log('MenuContainersController: error when trying to re-order.');
                        brick.refresh();
                     }
                  })
                 .start();
        };

        this._containers = new Sortable(
            brickElement.find('.menu-config-container').get(0),
            {
                group: brickElement.attr('id'),
                animation: 150,
                onSort: onSortEventHandler
            }
        );

        this._brick = brick;
        return this;
    },

    isBound: function() {
        return Object.isNone(this._brick) === false;
    }
});
