(function($) {
"use strict";

var MockActionBuilderRegistry = creme.component.FactoryRegistry.sub({
    _init_: function(context, options) {
        this._super_(creme.component.FactoryRegistry, '_init_', options);
        this.context = context;
    },

    _build_a: function(options) {
        return this.context.mockActionA;
    },
    _build_b: function(options) {
        return this.context.mockActionB;
    },
    _build_do_it: function(options) {
        return this.context.mockActionDoIt;
    },
    _build_raises: function(options) {
        return this.context.mockActionRaises;
    },
    _build_slow: function(options) {
        return this.context.mockActionSlow;
    },
    _build_none: function(options) {
        return null;
    }
});

QUnit.module("creme.actionlink.js", new QUnitMixin(QUnitEventMixin, {
    beforeEach: function() {
        this.resetMockActionCalls();

        var actionCalls = this._mockActionCalls;
        var self = this;

        this.mockActionA = new creme.component.Action(function(options) {
            actionCalls.push('a');
            this.done();
        });

        this.mockActionB = new creme.component.Action(function(options) {
            actionCalls.push('b');
            this.done();
        });

        this.mockActionDoIt = new creme.component.Action(function(options) {
            actionCalls.push('do-it');
            this.done();
        });

        this.mockActionRaises = new creme.component.Action(function(options) {
            throw Error('this is an error !');
        });

        this.mockActionSlow = new creme.component.TimeoutAction({delay: 200});
        this.mockActionSlow.onDone(function() {
            actionCalls.push('slow');
        });

        this.mockActionBuilderDict = {
            a: function(options) {
                return self.mockActionA;
            },
            b: function(options) {
                return self.mockActionB;
            },
            'do-it': function(options) {
                return self.mockActionDoIt;
            },
            raises: function(options) {
                return self.mockActionRaises;
            },
            slow: function(options) {
                return self.mockActionSlow;
            },
            none: function(options) {
                return null;
            }
        };
    },

    resetMockActionCalls: function() {
        this._mockActionCalls = [];
    },

    mockActionCalls: function() {
        return this._mockActionCalls;
    },

    mapLinkStartEventType: function(d) {
        var uievent = d.length > 4 ? d[4] : undefined;
        var data = d.slice(0, 4);

        if (uievent) {
            data.push(uievent.type);
        }

        return data;
    }
}));

QUnit.test('creme.action.ActionLink', function(assert) {
    var action = new creme.action.ActionLink();
    assert.equal(false, action.isRunning());
    assert.equal(false, action.isBound());
});

QUnit.test('creme.action.ActionLink (unbind, not bound)', function(assert) {
    var action = new creme.action.ActionLink();
    assert.equal(false, action.isRunning());
    assert.equal(false, action.isBound());

    this.assertRaises(function() {
        action.unbind();
    }, Error, 'Error: action link is not bound');
});

QUnit.test('creme.action.ActionLink (unbind)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="a"></a>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link);

    assert.equal(false, action.isRunning());
    assert.equal(true, action.isBound());

    action.unbind();

    assert.equal(false, action.isRunning());
    assert.equal(false, action.isBound());
});

QUnit.test('creme.action.ActionLink (bind, no builder)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="a"></a>');

    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(true, link.is('.is-disabled'));
    assert.equal(true, action.isDisabled());

    link.trigger('click');
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.action.ActionLink (bind, invalid builder)', function(assert) {
    var action = new creme.action.ActionLink({debounce: 0});

    this.assertRaises(function() {
        action.builders('not a builder');
    }, Error, 'Error: action builder "not a builder" is not valid');

    this.assertRaises(function() {
        action.builders(15877);
    }, Error, 'Error: action builder "15877" is not valid');
});

QUnit.test('creme.action.ActionLink (bind, empty action)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .on('action-link-cancel', this.mockListener('cancel'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(true, link.is('.is-disabled'));
    assert.equal(true, action.isDisabled());

    link.trigger('click');
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual({}, this.mockListenerCalls());
});

QUnit.test('creme.action.ActionLink (bind, href)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="/actions/" data-action="a"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound(), 'is bound');
    assert.equal(false, link.is('.is-disabled'), 'is not disabled');
    assert.equal(false, action.isDisabled(), 'is not disabled');

    link.trigger('click');
    assert.deepEqual(['a'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionA]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, registry fallback)', function(assert) {
    var action = new creme.action.ActionLink({debounce: 0});
    var registry = new MockActionBuilderRegistry(this);
    var link = $('<a href="/actions/" data-action="a"/>');

    action.builders(registry);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound(), 'is bound');
    assert.equal(false, link.is('.is-disabled'), 'is not disabled');
    assert.equal(false, action.isDisabled(), 'is not disabled');

    link.trigger('click');
    assert.deepEqual(['a'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionA]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, registry custom)', function(assert) {
    var actionCalls = this._mockActionCalls;
    var action = new creme.action.ActionLink({debounce: 0});
    var registry = new MockActionBuilderRegistry(this);
    var link = $('<a href="/actions/" data-action="custom-a"/>');
    var customActionA = new creme.component.Action(function(options) {
        actionCalls.push('custom-a');
        this.done();
    });

    registry.register('custom-a', function(options) {
        return customActionA;
    });

    action.builders(registry);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound(), 'is bound');
    assert.equal(false, link.is('.is-disabled'), 'is not disabled');
    assert.equal(false, action.isDisabled(), 'is not disabled');

    link.trigger('click');
    assert.deepEqual(['custom-a'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], customActionA]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, data-action-url)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, actiontype with -)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="/actions/" data-action="do-it"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['do-it'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, unknown actiontype)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="unknown"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link);

    assert.equal(true, action.isBound());
    assert.equal(true, link.is('.is-disabled'));
    assert.equal(true, action.isDisabled());
});

QUnit.test('creme.action.ActionLink (bind, unknown actiontype, strict)', function(assert) {
    var action = new creme.action.ActionLink({strict: true});
    var link = $('<a data-action="unknown"/>');

    action.builders(this.mockActionBuilderDict);

    this.assertRaises(function() {
        action.bind(link);
    }, Error, 'Error: no such builder "unknown"');

    assert.equal(false, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());
});

QUnit.test('creme.action.ActionLink (bind, function builder)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="unknown"/>');
    var self = this;

    action.builders(function(actiontype) {
        return function() {
            return self.mockActionDoIt;
        };
    });
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['do-it'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', undefined, {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, action raises)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="raises"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([['action-link-start', undefined, {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-fail', [Error('this is an error !')], this.mockActionRaises]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, action none)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a data-action="none"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start'));
    assert.deepEqual([], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (already bound)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<a href="a"/>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link);

    this.assertRaises(function() {
        action.bind(link);
    }, Error, 'Error: action link is already bound');
});

QUnit.test('creme.action.ActionLink (bind, text/json data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"><script type="text/json"><!--{"data": 23}--></script></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, 23, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, application/json data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"><script type="application/json"><!--{"data": 23}--></script></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, 23, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, multiple data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b">' +
                    '<script type="text/json"><!-- {"data": "first"} --></script>' +
                    '<script type="application/json"><!--{"data": 23}--></script>' +
                 '</span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, 'first', 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind, invalid data)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"><script type="text/json"><!--{"data": 23}}}--></script></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (ignore click, disabled)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="do-it" class="is-disabled"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(true, link.is('.is-disabled'));
    assert.equal(true, action.isDisabled());

    link.trigger('click');

    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    link.removeClass('is-disabled');

    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');

    assert.deepEqual(['do-it'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (ignore click while running)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="slow"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    assert.equal(false, action.isRunning());

    link.trigger('click');
    assert.equal(true, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    link.trigger('click');
    assert.equal(true, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    var done = assert.async();

    var mockActionCalls = this.mockActionCalls.bind(this);
    var mockListenerCalls = this.mockListenerCalls.bind(this);
    var mockActionSlow = this.mockActionSlow;
    var mapLinkStartEventType = this.mapLinkStartEventType.bind(this);

    setTimeout(function() {
        assert.equal(false, action.isRunning());
        assert.deepEqual(['slow'], mockActionCalls());
        assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], mockListenerCalls('start').map(mapLinkStartEventType));
        assert.deepEqual([['action-link-done', [{delay: 200}], mockActionSlow]], mockListenerCalls('complete'));
        done();
    }, 300);
});

QUnit.test('creme.action.ActionLink (debounce click, 200ms delay)', function(assert) {
    var action = new creme.action.ActionLink({debounce: 200});
    var link = $('<span data-action-url="/actions/" data-action="b"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());
    assert.equal(false, action.isRunning());
    assert.equal(200, action._optDebounceDelay(link));

    link.trigger('click');
    assert.equal(false, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    link.trigger('click');
    link.trigger('click');
    link.trigger('click');

    assert.equal(false, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    var done = assert.async();

    var mockActionCalls = this.mockActionCalls.bind(this);
    var mockListenerCalls = this.mockListenerCalls.bind(this);
    var mockActionB = this.mockActionB;
    var mapLinkStartEventType = this.mapLinkStartEventType.bind(this);

    setTimeout(function() {
        assert.equal(false, action.isRunning());
        assert.deepEqual(['b'], mockActionCalls());
        assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], mockListenerCalls('start').map(mapLinkStartEventType));
        assert.deepEqual([['action-link-done', [], mockActionB]], mockListenerCalls('complete'));
        done();
    }, 300);
});

QUnit.test('creme.action.ActionLink (debounce click, 150ms delay from attrs)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b" data-debounce="150"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());
    assert.equal(false, action.isRunning());
    assert.equal(150, action._optDebounceDelay(link));

    link.trigger('click');
    assert.equal(false, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    link.trigger('click');
    link.trigger('click');
    link.trigger('click');

    assert.equal(false, action.isRunning());
    assert.deepEqual([], this.mockActionCalls());
    assert.deepEqual([], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([], this.mockListenerCalls('complete'));

    var done = assert.async();

    var mockActionCalls = this.mockActionCalls.bind(this);
    var mockListenerCalls = this.mockListenerCalls.bind(this);
    var mockActionB = this.mockActionB;
    var mapLinkStartEventType = this.mapLinkStartEventType.bind(this);

    setTimeout(function() {
        assert.equal(false, action.isRunning());
        assert.deepEqual(['b'], mockActionCalls());
        assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], mockListenerCalls('start').map(mapLinkStartEventType));
        assert.deepEqual([['action-link-done', [], mockActionB]], mockListenerCalls('complete'));
        done();
    }, 300);
});

QUnit.test('creme.action.ActionLink (not debounce click)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="b"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .onComplete(this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());
    assert.equal(false, action.isRunning());
    assert.equal(0, action._optDebounceDelay(link));

    link.trigger('click');
    assert.equal(false, action.isRunning());
    assert.deepEqual(['b'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionB]], this.mockListenerCalls('complete'));

    link.trigger('click');
    link.trigger('click');
    link.trigger('click');

    assert.equal(false, action.isRunning());
    assert.deepEqual(['b', 'b', 'b', 'b'], this.mockActionCalls());
    assert.deepEqual([
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click']
    ], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([
        ['action-link-done', [], this.mockActionB],
        ['action-link-done', [], this.mockActionB],
        ['action-link-done', [], this.mockActionB],
        ['action-link-done', [], this.mockActionB]
    ], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (bind event once)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="do-it"></span>');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .one('action-link-done', this.mockListener('complete'));

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');

    assert.deepEqual(['do-it'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));

    link.trigger('click');
    link.trigger('click');
    link.trigger('click');

    assert.deepEqual(['do-it', 'do-it', 'do-it', 'do-it'], this.mockActionCalls());
    assert.deepEqual([
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click']
    ], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

QUnit.test('creme.action.ActionLink (unbind event)', function(assert) {
    var action = new creme.action.ActionLink();
    var link = $('<span data-action-url="/actions/" data-action="do-it"></span>');
    var complete_cb = this.mockListener('complete');

    action.builders(this.mockActionBuilderDict);
    action.bind(link)
          .on('action-link-start', this.mockListener('start'))
          .on('action-link-done', complete_cb);

    assert.equal(true, action.isBound());
    assert.equal(false, link.is('.is-disabled'));
    assert.equal(false, action.isDisabled());

    link.trigger('click');

    assert.deepEqual(['do-it'], this.mockActionCalls());
    assert.deepEqual([['action-link-start', '/actions/', {}, {}, 'click']], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));

    action.off('action-link-done', complete_cb);

    link.trigger('click');
    link.trigger('click');
    link.trigger('click');

    assert.deepEqual(['do-it', 'do-it', 'do-it', 'do-it'], this.mockActionCalls());
    assert.deepEqual([
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click'],
        ['action-link-start', '/actions/', {}, {}, 'click']
    ], this.mockListenerCalls('start').map(this.mapLinkStartEventType));
    assert.deepEqual([['action-link-done', [], this.mockActionDoIt]], this.mockListenerCalls('complete'));
});

}(jQuery));
