define(
[
    'splunk_monitoring_console/views/settings/forwarder_setup/enterprise/RebuildAssetsDialog'
], function(
    RebuildAssetsDialog
) {
    suite('Build Assets Now', function() {
        setup(function() {
            this.view = new RebuildAssetsDialog();

            assert.ok(this.view, 'dialog created');
        });

        teardown(function() {

        });

        test('search manager', function() {
            this.view._runRebuildSearch();
            assert.ok(this.view._rebuildForwarderAssetsSearch, 'search manager should have been created');
        });

        test('render', function() {
            this.view.render();

            assert.ok(this.view.children.timeRangePicker, 'DOM should have been created');
        });
    });
});