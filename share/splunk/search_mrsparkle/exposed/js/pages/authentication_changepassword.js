define([
        'routers/Changepassword',
        'util/router_utils'
    ],
    function(
        ChangepasswordRouter,
        router_utils
    ) {
        var changepasswordRouter = new ChangepasswordRouter();
        router_utils.start_backbone_history();
    }
);