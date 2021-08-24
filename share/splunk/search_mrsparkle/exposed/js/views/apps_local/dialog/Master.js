define([
        'views/shared/apps_remote/dialog/Master',
        'uri/route'
    ],
    function(
        AppsRemoteMaster,
        route
    ) {
        return AppsRemoteMaster.extend({
            returnToURL: function() {
                return route.appsLocal(this.model.application.get('root'), this.model.application.get('locale'), this.model.application.get('app'));
            }
        });
    });
