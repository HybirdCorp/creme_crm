(function($) {
QUnit.module("creme.component.action.js", new QUnitMixin(QUnitEventMixin, {
    mockBindActionListeners: function(action) {
        var done = this.mockListener('done_cb'),
            failed = this.mockListener('fail_cb'),
            canceled = this.mockListener('cancel_cb');

        return action.onCancel(canceled)
                     .onDone(done)
                     .onFail(failed);
    },

    mockAction: function() {
        var action = new creme.component.Action();
        var run = this.mockListener('run_cb');

        return this.mockBindActionListeners(action.action(run));
    }
}));

QUnit.test('creme.component.Action (options)', function(assert) {
    var action = new creme.component.Action();
    assert.deepEqual({}, action.options());

    assert.deepEqual(action, action.options({a: 1, b: 12}));
    assert.deepEqual({a: 1, b: 12}, action.options());

    assert.equal(false, action.isRunning());
    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    assert.equal(action.done, action.action());

    assert.deepEqual(action, action.action(run));
    assert.equal(run, action.action());

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());

    action.start({a: 12});

    assert.deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    assert.equal('run', action.status());
    assert.equal(true, action.isRunning());
});

QUnit.test('creme.component.Action (start, extra args)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    action.action(run)
          .start({a: 12}, 145, 'a');

    assert.deepEqual({
        'run_cb': [[{a: 12}, 145, 'a']]
    }, this.mockListenerCalls());

    assert.equal('run', action.status());
    assert.equal(true, action.isRunning());

    assert.equal(false, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, default)', function(assert) {
    var action = new creme.component.Action();
    var done = this.mockListener('done_cb'),
        failed = this.mockListener('fail_cb'),
        canceled = this.mockListener('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed);

    assert.equal(action.done, action.action());

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());

    action.start({a: 12});

    assert.deepEqual({
        'done_cb': [['done', {a: 12}]]
    }, this.mockListenerCalls());

    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, constant)', function(assert) {
    var action = new creme.component.Action();
    var done = this.mockListener('done_cb'),
        failed = this.mockListener('fail_cb'),
        canceled = this.mockListener('cancel_cb');

    action.onCancel(canceled)
          .onDone(done)
          .onFail(failed)
          .action('constant');

    assert.equal(true, Object.isFunc(action.action()));

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());

    action.start({a: 12});

    assert.deepEqual({
        'done_cb': [['done', 'constant']]
    }, this.mockListenerCalls());

    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (start, already running)', function(assert) {
    var action = new creme.component.Action();
    var run = this.mockListener('run_cb');

    assert.equal(action.done, action.action());

    assert.deepEqual(action, action.action(run));
    assert.equal(run, action.action());

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());

    action.start({a: 12});

    assert.deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    assert.equal('run', action.status());
    assert.equal(true, action.isRunning());

    action.start({b: 15.8});

    assert.deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    assert.equal('run', action.status());
    assert.equal(true, action.isRunning());
});

QUnit.test('creme.component.Action (done)', function(assert) {
    var action = this.mockAction();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());

    action.start({a: 12});

    assert.deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    assert.equal(true, action.isRunning());

    action.done();

    assert.deepEqual({
        'run_cb': [[{a: 12}]],
        'done_cb': [['done']]
    }, this.mockListenerCalls());

    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (done, parameter)', function(assert) {
    var action = this.mockAction();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());

    action.start({a: 12});

    assert.deepEqual({
        'run_cb': [[{a: 12}]]
    }, this.mockListenerCalls());

    assert.equal(true, action.isRunning());

    action.done({b: 153});

    assert.deepEqual({
        'run_cb': [[{a: 12}]],
        'done_cb': [['done', {b: 153}]]
    }, this.mockListenerCalls());

    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (done, not running)', function(assert) {
    var action = this.mockAction();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());

    action.done();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (fail)', function(assert) {
    var action = this.mockAction();

    action.start();

    assert.deepEqual({
        'run_cb': [[]]
    }, this.mockListenerCalls());

    assert.equal(true, action.isRunning());

    action.fail();

    assert.deepEqual({
        'run_cb': [[]],
        'fail_cb': [['fail']]
    }, this.mockListenerCalls());

    assert.equal('fail', action.status());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (fail, not running)', function(assert) {
    var action = this.mockAction();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());

    action.fail();

    assert.deepEqual({}, this.mockListenerCalls());
    assert.equal(false, action.isRunning());

    assert.equal(true, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (fail, run exception)', function(assert) {
    var action = this.mockAction();
    var error = new Error('fail test !');

    action.action(function() {
                      throw error;
                  })
          .start();

    assert.deepEqual({
        'fail_cb': [['fail', error]]
    }, this.mockListenerCalls());

    assert.equal('fail', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(false, action.isStatusDone());
    assert.equal(true, action.isStatusFail());
    assert.equal(false, action.isStatusCancel());
});

QUnit.test('creme.component.Action (fail from action)', function(assert) {
    var action = this.mockAction();

    action.action(function() {
                      this.fail('fail test', 145);
                  })
          .start();

    assert.deepEqual({
        'fail_cb': [['fail', 'fail test', 145]]
    }, this.mockListenerCalls());

    assert.equal('fail', action.status());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (cancel)', function(assert) {
    var action = this.mockAction();

    action.start();

    assert.deepEqual({
        'run_cb': [[]]
    }, this.mockListenerCalls());

    assert.equal(true, action.isRunning());

    action.cancel();

    assert.deepEqual({
        'run_cb': [[]],
        'cancel_cb': [['cancel']]
    }, this.mockListenerCalls());

    assert.equal('cancel', action.status());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (cancel from action)', function(assert) {
    var action = this.mockAction();

    action.action(function() {
                      this.cancel('cancel test', 8);
                  })
          .start();

    assert.deepEqual({
        'cancel_cb': [['cancel', 'cancel test', 8]]
    }, this.mockListenerCalls());

    assert.equal('cancel', action.status());
    assert.equal(false, action.isRunning());

    assert.equal(false, action.isStatusDone());
    assert.equal(false, action.isStatusFail());
    assert.equal(true, action.isStatusCancel());
});

QUnit.test('creme.component.Action (onStart)', function(assert) {
    var action = this.mockAction();

    action.onStart(this.mockListener('start_cb'))
          .action(function() {
                      this.done('ok');
                  })
          .start('start test', 4);

    assert.deepEqual({
        'start_cb': [['start', 'start test', 4]],
        'done_cb': [['done', 'ok']]
    }, this.mockListenerCalls());
});

QUnit.test('creme.component.Action (trigger)', function(assert) {
    var action = this.mockAction();

    action.on('event1', this.mockListener('1'));
    action.action(function() {
                      this.trigger('event1', 2);
                      this.done();
                  })
          .start();

    assert.deepEqual({
        '1': [['event1', 2]],
        'done_cb': [['done']]
    }, this.mockListenerCalls());

    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (off event)', function(assert) {
    var action = this.mockAction();

    action.off('done');
    action.on('event1', this.mockListener('1'));
    action.action(function() {
                      this.trigger('event1', 2);
                      this.done();
                  })
          .start();

    assert.deepEqual({
        '1': [['event1', 2]]
    }, this.mockListenerCalls());

    assert.equal('done', action.status());
    assert.equal(false, action.isRunning());
});

QUnit.test('creme.component.Action (delegate)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    assert.equal(false, delegate.isRunning());
    assert.equal(false, action.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    delegate.action(12).start();

    assert.deepEqual({
        'done_cb': [['done', 12], ['done', 12]]
    }, this.mockListenerCalls());

    assert.equal('done', delegate.status());
    assert.equal('done', action.status());
});

QUnit.test('creme.component.Action (delegate, cancel)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    assert.equal(false, delegate.isRunning());
    assert.equal(false, action.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    delegate.action(function() {
        this.cancel('canceled !');
    }).start();

    assert.deepEqual({
        'cancel_cb': [['cancel', 'canceled !'], ['cancel', 'canceled !']]
    }, this.mockListenerCalls());

    assert.equal('cancel', delegate.status());
    assert.equal('cancel', action.status());
});

QUnit.test('creme.component.Action (delegate, fail)', function(assert) {
    var delegate = this.mockBindActionListeners(new creme.component.Action());
    var action = this.mockBindActionListeners(new creme.component.Action());

    action.delegate(delegate);

    assert.equal(false, delegate.isRunning());
    assert.equal(false, action.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    delegate.action(function() {
        this.fail('failed !');
    }).start();

    assert.deepEqual({
        'fail_cb': [['fail', 'failed !'], ['fail', 'failed !']]
    }, this.mockListenerCalls());

    assert.equal('fail', delegate.status());
    assert.equal('fail', action.status());
});

QUnit.test('creme.component.Action (after)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first)
          .action(function(value) {
                      this.result = value * 10;
                      this.done(this.result);
                  });

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.action(12).start();
    assert.deepEqual({
        'done_cb': [['done', 12], ['done', NaN]]
    }, this.mockListenerCalls());

    assert.equal(true, isNaN(second.result));
    assert.equal('done', first.status());
    assert.equal('done', second.status());
});

QUnit.test('creme.component.Action (after, passArgs)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first, {passArgs: true})
          .action(function(value) {
                      this.result = value * 10;
                      this.done(this.result);
                  });

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.action(12).start();
    assert.deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    assert.equal(12 * 10, second.result);
    assert.equal('done', first.status());
    assert.equal('done', second.status());
});

QUnit.test('creme.component.Action (after, invalid)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    this.assertRaises(function() {
        second.after({});
    }, Error, 'Error: This is not an action instance');

    assert.deepEqual([], second.stack());
    assert.deepEqual([], first.stack());

    second.after(first);

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    this.assertRaises(function() {
        second.after(first);
    }, Error, 'Error: Action is already after');

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());
});

QUnit.test('creme.component.Action (after, second fail)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.after(first, {passArgs: true})
          .action(function(value) {
                      this.fail(value);
                  });

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.action(115).start();

    assert.deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    assert.equal(undefined, second.result);
    assert.equal('done', first.status());
    assert.equal('fail', second.status());
});

QUnit.test('creme.component.Action (after, first fail)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    first.action(function(value) {
        this.fail(value);
    });

    second.after(first, {passArgs: true});

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.start(115);

    assert.deepEqual({
        'fail_cb': [['fail', 115], ['fail', 115]]
    }, this.mockListenerCalls());

    assert.equal('fail', first.status());
    assert.equal('fail', second.status());
});

QUnit.test('creme.component.Action (after, first cancel)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    first.action(function(value) {
        this.cancel(value);
    });

    second.after(first, {passArgs: true});

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.start(115);

    assert.deepEqual({
        'cancel_cb': [['cancel', 115], ['cancel', 115]]
    }, this.mockListenerCalls());

    assert.equal('cancel', first.status());
    assert.equal('cancel', second.status());
});

QUnit.test('creme.component.Action (listen, after alias)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.listen(first, {passArgs: true})
          .action(function(value) {
                      if (value < 100) {
                          this.result = value * 10;
                          this.done(this.result);
                      } else {
                          this.fail(value);
                      }
                  });

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.action(12).start();

    assert.deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    assert.equal(12 * 10, second.result);
    assert.equal('done', first.status());
    assert.equal('done', second.status());

    second.result = undefined;
    this.resetMockListenerCalls();

    first.action(115).start();

    assert.deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    assert.equal(undefined, second.result);
    assert.equal('done', first.status());
    assert.equal('fail', second.status());
});

QUnit.test('creme.component.Action (before)', function(assert) {
    var first = this.mockBindActionListeners(new creme.component.Action());
    var second = this.mockBindActionListeners(new creme.component.Action());

    second.action(function(value) {
                      if (value < 100) {
                          this.result = value * 10;
                          this.done(this.result);
                      } else {
                          this.fail(value);
                      }
                  });

    first.before(second, {passArgs: true});

    assert.deepEqual([first], second.stack());
    assert.deepEqual([], first.stack());

    assert.equal(undefined, second.result);
    assert.equal(false, first.isRunning());
    assert.equal(false, second.isRunning());

    assert.deepEqual({}, this.mockListenerCalls());

    first.action(12).start();

    assert.deepEqual({
        'done_cb': [['done', 12], ['done', 12 * 10]]
    }, this.mockListenerCalls());

    assert.equal(12 * 10, second.result);
    assert.equal('done', first.status());
    assert.equal('done', second.status());

    second.result = undefined;
    this.resetMockListenerCalls();

    first.action(115).start();

    assert.deepEqual({
        'done_cb': [['done', 115]],
        'fail_cb': [['fail', 115]]
    }, this.mockListenerCalls());

    assert.equal(undefined, second.result);
    assert.equal('done', first.status());
    assert.equal('fail', second.status());
});

QUnit.test('creme.component.TimeoutAction (zero delay)', function(assert) {
    var action = this.mockBindActionListeners(new creme.component.TimeoutAction({delay: 0}));
    action.start();

    // stops immediately
    assert.equal(false, action.isRunning());
    assert.equal('done', action.status());

    assert.deepEqual({
        'done_cb': [['done', {delay: 0}]]
    }, this.mockListenerCalls());
});

QUnit.test('creme.component.TimeoutAction (200ms delay)', function(assert) {
    var timeout = this.mockBindActionListeners(new creme.component.TimeoutAction({delay: 200}));
    var action = this.mockBindActionListeners(new creme.component.Action());
    var mockListenerCalls = this.mockListenerCalls.bind(this);

    timeout.before(action).start();

    assert.equal(true, timeout.isRunning());
    assert.equal(false, action.isRunning());
    assert.deepEqual({}, this.mockListenerCalls());

    var done = assert.async();

    setTimeout(function() {
        assert.equal(false, timeout.isRunning());
        assert.equal(false, action.isRunning());

        assert.deepEqual({
            'done_cb': [['done', {delay: 200}], ['done']]
        }, mockListenerCalls());

        done();
    }, 300);
});

}(jQuery));
