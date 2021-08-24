define(
[
    'mocks/models/MockSplunkD',
    'mocks/collections/MockSplunkDs',
    'splunk_monitoring_console/routers/MonitoringConsoleForwarderSetup',
    'splunk_monitoring_console/views/settings/forwarder_setup/enterprise/Master',
    'splunk_monitoring_console/views/settings/forwarder_setup/lite/Master',
    'util/qunit_utils'
], function(
    MockSplunkD,
    MockSplunkDs,
    Router,
    MasterView,
    MasterLightView,
    qunitUtils
) {
    var LOCALE = "en-US";
    var APP = "splunk_monitoring_console";
    var PAGE = "managementconsole_forwarder_setup";

    suite('DMC Forwarder Setup Router', function() {
        util(qunitUtils.SplunkdPartials);

        setup(function() {
            this.router = new Router();
            sinon.spy(MasterView.prototype, 'initialize');
            sinon.spy(MasterLightView.prototype, 'initialize');

            this.router.deferreds.pageViewRendered.resolve();
            this.router.deferreds.searchesCollectionDfd.resolve();
            this.router.pageView = {};
            this.router.collection.searchesCollection = new MockSplunkDs();
            this.router.collection.searchesCollection.add(new MockSplunkD());

            this.serverInfoStub = sinon.stub(this.router.model.serverInfo, 'isLite');

            assert.ok(this.router, 'router created');
        });

        teardown(function() {
            MasterView.prototype.initialize.restore();
            MasterLightView.prototype.initialize.restore();
            this.serverInfoStub.restore();
        });

        test('initialize enterprise view:', function() {
            this.serverInfoStub.returns(false);
            this.router.page(LOCALE, APP, PAGE);
            assert.equal(MasterView.prototype.initialize.callCount, 1, 'Enterprise Master View should be instantiated once');
        });
        test('initialize light view:', function() {
            this.serverInfoStub.returns(true);
            this.router.collection.searchesCollection.models[0].entry.content.set('disabled', true);
            this.router.page(LOCALE, APP, PAGE);
            assert.equal(MasterLightView.prototype.initialize.callCount, 1, 'Lite Master View should be instantiated once');
        });
    });
});
