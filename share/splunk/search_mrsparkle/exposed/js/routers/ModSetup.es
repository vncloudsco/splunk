import _ from 'underscore';
import $ from 'jquery';
import BaseRouter from 'routers/Base';
import ModSetupView from 'views/modsetup/Master';
import ModSetupConfigurationManager from 'helpers/modsetup/configuration/ModSetupConfigurationManager';
import classicurlModel from 'models/classicurl';

export default BaseRouter.extend({

    initialize(...args) {
        BaseRouter.prototype.initialize.apply(this, args);
        this.setPageTitle(_('Mod setup').t());
        this.enableAppBar = false;
        this.showAppsList = false;
        if (!_.isUndefined(args.supportedExtensions)) {
            this.supportedExtensions = args.supportedExtensions;
        }

        this.model.classicurl = classicurlModel;
        this.deferreds.classicurl = this.model.classicurl.fetch();
    },

    page(...args) {
        BaseRouter.prototype.page.apply(this, args);
        $.when(this.deferreds.classicurl).then(() => {
            const editAction = this.model.classicurl.get('action');
            const modSetupConfigurationManager = new ModSetupConfigurationManager({
                app: this.model.application.get('app'),
                isDMCEnabled: false,
                isEditAll: (editAction && editAction === 'edit'),
            });

            $.when(modSetupConfigurationManager.fetchConfigAppsList(this.model.application.get('app'))).done(() => {
                const masterViewOptions = {
                    configurationManager: modSetupConfigurationManager,
                    model: {
                        application: this.model.application,
                        classicurl: this.model.classicurl,
                    },
                    collection: {},
                };
                if (!_.isUndefined(this.supportedExtensions)) {
                    masterViewOptions.supportedExtensions = this.supportedExtensions;
                }
                if (modSetupConfigurationManager.requiresSetup()) {
                    $('.preload').replaceWith(this.pageView.el);
                    this.masterView = new ModSetupView(masterViewOptions);
                    this.pageView.$('.main-section-body').append(this.masterView.render().el);
                }
            });
        });
    },
});
