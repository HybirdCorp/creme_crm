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

    equal(true, brick.isBound());
    equal(true, brick.menu().isBound());

    this.assertRaises(function() {
        brick.menu().bind(element);
    }, Error, 'Error: BrickMenu is already bound');

    brick.unbind();

    equal(false, brick.isBound());
    equal(false, brick.menu().isBound());

    this.assertRaises(function() {
        brick.menu().unbind();
    }, Error, 'Error: BrickMenu is not bound');
});

QUnit.test('creme.bricks.Brick.menu (toggle, not bound)', function(assert) {
    var brick = new creme.bricks.Brick();

    equal(false, brick.isBound());
    equal(false, brick.menu().isOpened());
    equal(false, brick.menu().isBound());
    equal(true, brick.menu().isDisabled());
    equal(0, brick._actionLinks.length);

    brick.menu().open();
    equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    equal(false, brick.menu().isOpened());
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
    equal(true, brick.isBound());

    equal(false, brick.menu().isOpened());
    equal(true, brick.menu().isDisabled());
    equal(true, element.find('.brick-header-menu').is('.is-disabled'));
    equal(0, brick._actionLinks.length);

    brick.menu().open();
    equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    equal(false, brick.menu().isOpened());

    brick.toggleMenu();
    equal(false, brick.menu().isOpened());
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
    equal(true, brick.isBound());

    equal(false, brick.menu().isOpened());
    equal(false, brick.menu().isDisabled());
    equal(false, element.find('.brick-header-menu').is('.is-disabled'));
    equal(1, brick._actionLinks.length);

    brick.menu().open();
    equal(true, brick.menu().isOpened());
    equal('<div class="brick-menu-buttons"><a data-action="collapse"></a></div>', brick.menu()._dialog.content().html());

    brick.menu().toggle();
    equal(false, brick.menu().isOpened());

    brick.menu().toggle();
    equal(true, brick.menu().isOpened());

    brick.toggleMenu();
    equal(false, brick.menu().isOpened());

    brick.toggleMenu();
    equal(true, brick.menu().isOpened());
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
    equal(true, brick.isBound());

    equal(false, brick.menu().isOpened());
    equal(false, brick.menu().isDisabled());
    equal(false, element.find('.brick-header-menu').is('.is-disabled'));
    equal(1, brick._actionLinks.length);

    equal(false, brick.menu().isOpened());

    element.find('.brick-header-menu').trigger('click');
    equal(true, brick.menu().isOpened());

    element.find('.brick-header-menu').trigger('click');
    equal(false, brick.menu().isOpened());
});

}(jQuery));
