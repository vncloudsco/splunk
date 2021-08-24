define(['splunk_monitoring_console/routers/MonitoringConsoleAlertsSetup', 'util/router_utils'], function(MonitoringConsoleAlertsSetupRouter, router_utils) {
    var monitoringConsoleAlertsSetupRouter = new MonitoringConsoleAlertsSetupRouter();
    router_utils.start_backbone_history();
});
