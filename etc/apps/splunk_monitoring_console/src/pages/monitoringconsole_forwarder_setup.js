define(['splunk_monitoring_console/routers/MonitoringConsoleForwarderSetup', 'util/router_utils'], function(MonitoringConsoleForwarderSetupRouter, router_utils) {
    var monitoringConsoleForwarderSetupRouter = new MonitoringConsoleForwarderSetupRouter();
    router_utils.start_backbone_history();
});
