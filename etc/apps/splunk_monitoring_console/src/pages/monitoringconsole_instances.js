define(['splunk_monitoring_console/routers/MonitoringConsoleInstances', 'util/router_utils'], function(MonitoringConsoleInstancesRouter, router_utils) {
    var monitoringConsoleInstancesRouter = new MonitoringConsoleInstancesRouter();
    router_utils.start_backbone_history();
});
