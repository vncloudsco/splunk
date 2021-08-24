define([
        'routers/PasswordManagement',
        'util/router_utils'
    ],
    function(
        PasswordManagementRouter,
        router_utils
    ) {
        var passwordManagementRouter = new PasswordManagementRouter();
        router_utils.start_backbone_history();
    }
);