(function($) {

QUnit.module("creme.billing.brick.actions", new QUnitMixin(QUnitEventMixin,
                                                          QUnitAjaxMixin,
                                                          QUnitBrickMixin,
                                                          QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;
        backend.options.enableUriSearch = true;
    },

    createBillingBrickTable: function(options) {
        options = $.extend({
            classes: ['billing-lines-brick']
        }, options || {});

        return this.createBrickTable(options);
    }
}));

QUnit.test('creme.billing.brick (available actions)', function(assert) {
    var brick = this.createBillingBrickTable().brick();

    equal(true, Object.isSubClassOf(brick.action('billing-line-addonfly'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-saveall'), creme.component.Action));
    equal(true, Object.isSubClassOf(brick.action('billing-line-clearonfly'), creme.component.Action));
});

}(jQuery));
