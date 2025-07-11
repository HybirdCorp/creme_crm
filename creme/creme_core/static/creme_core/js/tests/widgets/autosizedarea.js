/* globals QUnitWidgetMixin */ // BrowserVersion

(function($) {

QUnit.module("creme.widget.AutoSizedTextArea", new QUnitMixin(QUnitEventMixin, QUnitWidgetMixin, {
    afterEach: function() {
        creme.widget.shutdown(this.qunitFixture());
    }
}));

QUnit.test('creme.widget.AutoSizedTextArea.create (default)', function(assert) {
    var element = $(
        '<textarea widget="ui-creme-autosizedarea" class="ui-creme-autosizedarea ui-creme-widget widget-auto"></textarea>'
     ).appendTo(this.qunitFixture());

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.layout()._min, 2);
    assert.equal(widget.layout()._max, undefined);

    assert.equal(element.attr('rows'), String(2));
});

QUnit.test('creme.widget.AutoSizedTextArea.create (default min)', function(assert) {
    var element = $(
        '<textarea widget="ui-creme-autosizedarea" class="ui-creme-autosizedarea ui-creme-widget widget-auto" rows="3"></textarea>'
     ).appendTo(this.qunitFixture());

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.layout()._min, 3);
    assert.equal(widget.layout()._max, undefined);
    assert.equal(element.attr('rows'), String(3));
});

QUnit.test('creme.widget.AutoSizedTextArea.create (min/max)', function(assert) {
    var element = $(
        '<textarea widget="ui-creme-autosizedarea" class="ui-creme-autosizedarea ui-creme-widget widget-auto" rows="3" min-rows="2" max-rows="5"></textarea>'
     ).appendTo(this.qunitFixture());

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(widget.layout()._min, 2);
    assert.equal(widget.layout()._max, 5);
    assert.equal(element.attr('rows'), String(2));
});

}(jQuery));
