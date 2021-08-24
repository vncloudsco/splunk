define(
[
    'underscore',
    'splunk_monitoring_console/collections/Metrics',
    'fixtures/monitoringconsole/Metrics.json',
    'util/qunit_utils'
],
function (
    _,
    MetricsCollection,
    MetricsFixture,
    qunitUtils
) {
    suite('Setup', function() {
        util(qunitUtils.FakeXhrModule, {
            setup: function() {
                qunitUtils.FakeXhrModule.setup.call(this);
                this.metrics = new MetricsCollection();
                assert.ok(this.metrics, 'We should get no exceptions');
                assert.ok(true, 'Setup was successful');
            },
            teardown: function() {
                qunitUtils.FakeXhrModule.teardown.call(this);
                this.metrics.reset();
                assert.ok(true, 'Teardown was successful');
            }
        });

        test('Test fetch', function () {
            this.metrics.fetch();
            var request = this.requests[0];
            this.verifyRequestArgs(
                request,
                {
                    output_mode: 'json',
                    count: -1,
                    search: 'name=metric:*'
                },
                'Default args include count and search'
            );

        });

        test('test getMetrics', function() {
            var metrics = this.metrics.getMetrics();
            assert.equal(Object.keys(metrics).length, 0, 'There should be 0 metrics');

            var deferred = this.metrics.fetch();
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.notStrictEqual(deferred.state(), "resolved", 'request should not be resolved');

            var request = this.requests[0];
            this.respondTo(request, JSON.stringify(MetricsFixture))
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.strictEqual(deferred.state(), "resolved", 'request should be resolved');

            metrics = this.metrics.getMetrics();
            assert.equal(Object.keys(metrics).length, 7, 'should contain 7 metrics');
        });

        test('test getEnabledMetrics', function() {
            var metrics = this.metrics.getEnabledMetrics();
            assert.equal(Object.keys(metrics).length, 0, 'There should be 0 metrics');

            var deferred = this.metrics.fetch();
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.notStrictEqual(deferred.state(), "resolved", 'request should not be resolved');

            var request = this.requests[0];
            this.respondTo(request, JSON.stringify(MetricsFixture))
            assert.notStrictEqual(deferred.state(), "rejected", 'request should not be rejected');
            assert.strictEqual(deferred.state(), "resolved", 'request should be resolved');

            metrics = this.metrics.getEnabledMetrics();
            assert.equal(Object.keys(metrics).length, 3, 'should contain 3 metrics');
        });
    });
});
