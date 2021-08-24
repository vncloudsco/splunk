define([
        'routers/Users',
        'routers/AuthenticationUsers',
        'models/services/server/ServerInfo',
        'util/router_utils'
    ],
    function(
        UsersRouter,
        AuthUsersRouter,
        ServerInfoModel,
        router_utils
    ) {
        var serverInfo = new ServerInfoModel();
        var isLite, usersRouter;
        serverInfo.fetch({
            success: function(model, response) {
                isLite = serverInfo.isLite();
                if (isLite) {
                    usersRouter = new AuthUsersRouter();
                } else {
                    usersRouter = new UsersRouter();
                }
                router_utils.start_backbone_history();
            }.bind(this)
        });
    }
);