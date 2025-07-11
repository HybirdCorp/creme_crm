/* eslint operator-linebreak: ["error", "before"] */

(function($) {

QUnit.module("creme.bricks.menu", new QUnitMixin(QUnitEventMixin, QUnitAjaxMixin, QUnitBrickMixin));

QUnit.test('creme.bricks.Brick.menu (bind/unbind)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test">'
            + '<div class="brick-header">'
                + '<div class="brick-header-menu"></div>'
                + '<div class="brick-title">This is a title</div>'
            + '</div>'
        + '</div>');

    brick.bind(element);

    assert.equal(true, brick.isBound());
    assert.equal(true, brick.menu().isBound());

    this.assertRaises(function() {
        brick.menu().bind(element);
    }, Error, 'Error: BrickMenu is already bound');

    brick.unbind();

    assert.equal(false, brick.isBound());
    assert.equal(false, brick.menu().isBound());

    this.assertRaises(function() {
        brick.menu().unbind();
    }, Error, 'Error: BrickMenu is not bound');
});

QUnit.test('creme.bricks.Brick.menu (toggle, not bound)', function(assert) {
    var brick = new creme.bricks.Brick();

    assert.equal(false, brick.isBound());
    assert.equal(false, brick.menu().isOpened());
    assert.equal(false, brick.menu().isBound());
    assert.equal(true, brick.menu().isDisabled());
    assert.equal(0, brick._actionLinks.length);

    brick.menu().open();
    assert.equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    assert.equal(false, brick.menu().isOpened());
});

QUnit.test('creme.bricks.Brick.menu (toggle, empty)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test">'
            + '<div class="brick-header">'
                + '<div class="brick-header-menu"></div>'
                + '<div class="brick-title">This is a title</div>'
            + '</div>'
        + '</div>');

    brick.bind(element);
    assert.equal(true, brick.isBound());

    assert.equal(false, brick.menu().isOpened());
    assert.equal(true, brick.menu().isDisabled());
    assert.equal(true, element.find('.brick-header-menu').is('.is-disabled'));
    assert.equal(0, brick._actionLinks.length);

    brick.menu().open();
    assert.equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    assert.equal(false, brick.menu().isOpened());

    brick.toggleMenu();
    assert.equal(false, brick.menu().isOpened());
});

QUnit.test('creme.bricks.Brick.menu (toggle)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test">'
            + '<div class="brick-header">'
                + '<div class="brick-header-menu">'
                    + '<div class="brick-menu-buttons">'
                        + '<a data-action="collapse"></a>'
                    + '</div>'
                + '</div>'
                + '<div class="brick-title">This is a title</div>'
            + '</div>'
        + '</div>');

    brick.bind(element);
    assert.equal(true, brick.isBound());

    assert.equal(false, brick.menu().isOpened());
    assert.equal(false, brick.menu().isDisabled());
    assert.equal(false, element.find('.brick-header-menu').is('.is-disabled'));
    assert.equal(1, brick._actionLinks.length);

    brick.menu().open();
    assert.equal(true, brick.menu().isOpened());
    assert.equal('<div class="brick-menu-buttons"><a data-action="collapse"></a></div>', brick.menu()._dialog.content().html());

    brick.menu().toggle();
    assert.equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    assert.equal(true, brick.menu().isOpened());

    brick.toggleMenu();
    assert.equal(false, brick.menu().isOpened());

    brick.toggleMenu();
    assert.equal(true, brick.menu().isOpened());
});

QUnit.test('creme.bricks.Brick.menu (toggle click)', function(assert) {
    var brick = new creme.bricks.Brick();
    var element = $('<div class="brick ui-creme-widget" widget="brick" id="brick-for-test">'
            + '<div class="brick-header">'
                + '<div class="brick-header-menu">'
                    + '<div class="brick-menu-buttons">'
                        + '<a data-action="collapse"></a>'
                    + '</div>'
                + '</div>'
                + '<div class="brick-title">This is a title</div>'
            + '</div>'
        + '</div>');

    brick.bind(element);
    assert.equal(true, brick.isBound());

    assert.equal(false, brick.menu().isOpened());
    assert.equal(false, brick.menu().isDisabled());
    assert.equal(false, element.find('.brick-header-menu').is('.is-disabled'));
    assert.equal(1, brick._actionLinks.length);

    assert.equal(false, brick.menu().isOpened());

    element.find('.brick-header-menu').trigger('click');
    assert.equal(true, brick.menu().isOpened());

    element.find('.brick-header-menu').trigger('click');
    assert.equal(false, brick.menu().isOpened());
});

}(jQuery));
