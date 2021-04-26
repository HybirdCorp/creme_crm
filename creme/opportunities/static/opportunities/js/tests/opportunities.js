(function($) {

QUnit.module("creme.opportunities", new QUnitMixin(QUnitEventMixin,
                                                   QUnitAjaxMixin,
                                                   QUnitBrickMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/opports/15/quote/12/set_current': backend.response(200, ''),
            'mock/opports/15/quote/12/unset_current': backend.response(200, '')
        });
    }
}));

QUnit.test('creme.opportunities.QuoteController (bind)', function(assert) {
    var brick = this.createBrickWidget({
        content: '<input class="opportunities-current-quote" type="checkbox" data-url="mock/opports/15/quote/12/set_current">'
    }).brick();

    var controller = new creme.opportunities.QuoteController();

    equal(false, controller.isBound());

    controller.bind(brick);

    equal(true, controller.isBound());

    this.assertRaises(function() {
        controller.bind(brick);
    }, Error, 'Error: QuoteController is already bound');
});

QUnit.test('creme.opportunities.QuoteController (toggle)', function(assert) {
    var brick = this.createBrickWidget({
        content: '<input class="opportunities-current-quote" type="checkbox" data-url="mock/opports/15/quote/12/set_current">'
    }).brick();

    var controller = new creme.opportunities.QuoteController().bind(brick);

    equal(true, controller.isBound());
    deepEqual([], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick.element().find('.opportunities-current-quote').trigger('click');

    deepEqual([['POST', {}]], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([
        ['GET', {brick_id: ['brick-for-test'], extra_data: '{}'}]
    ], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.opportunities.QuoteController (toggle, disabled)', function(assert) {
    var brick = this.createBrickWidget({
        content: '<input class="opportunities-current-quote" type="checkbox" data-url="mock/opports/15/quote/12/set_current" disabled>'
    }).brick();

    var controller = new creme.opportunities.QuoteController().bind(brick);

    equal(true, controller.isBound());
    deepEqual([], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick.element().find('.opportunities-current-quote').trigger('click');

    deepEqual([], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

QUnit.test('creme.opportunities.QuoteController (toggle, no url)', function(assert) {
    var brick = this.createBrickWidget({
        content: '<input class="opportunities-current-quote" type="checkbox">'
    }).brick();

    var controller = new creme.opportunities.QuoteController().bind(brick);

    equal(true, controller.isBound());
    deepEqual([], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));

    brick.element().find('.opportunities-current-quote').trigger('click');

    deepEqual([], this.mockBackendUrlCalls('mock/opports/15/quote/12/set_current'));
    deepEqual([], this.mockBackendUrlCalls('mock/brick/all/reload'));
});

}(jQuery));
