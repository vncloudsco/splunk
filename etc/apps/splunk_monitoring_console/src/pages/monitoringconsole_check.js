define(['routers/MonitoringConsoleCheck', 'util/router_utils'], function(MonitoringConsoleCheckRouter, router_utils) {
    var monitoringConsoleCheckRouter = new MonitoringConsoleCheckRouter();
    router_utils.start_backbone_history();
});