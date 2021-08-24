define(['splunk_monitoring_console/routers/MonitoringConsoleOverview', 'util/router_utils'], function(MonitoringConsoleOverviewRouter, router_utils) {
    var monitoringConsoleOverviewRouter = new MonitoringConsoleOverviewRouter();
    router_utils.start_backbone_history();
});
