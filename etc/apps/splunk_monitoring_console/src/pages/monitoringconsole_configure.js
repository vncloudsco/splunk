define(['splunk_monitoring_console/routers/MonitoringConsoleConfigure', 'util/router_utils'], function(MonitoringConsoleConfigureRouter, router_utils) {
	var monitoringConsoleConfigureRouter = new MonitoringConsoleConfigureRouter();
	router_utils.start_backbone_history();
});
