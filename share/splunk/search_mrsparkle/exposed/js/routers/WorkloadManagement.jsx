import _ from 'underscore';
import $ from 'jquery';
import React from 'react';
import { render } from 'react-dom';
import BaseRouter from 'routers/Base';
import Category from 'collections/services/admin/workload_management/Category';
import Pools from 'collections/services/admin/workload_management/Pools';
import Rules from 'collections/services/admin/workload_management/Rules';
import Status from 'collections/services/admin/workload_management/Status';
import Checks from 'collections/services/admin/workload_management/config/PreflightChecks';
import Enable from 'models/services/admin/workload_management/Enable';
import Disable from 'models/services/admin/workload_management/Disable';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import WorkloadManagementPageContainer from 'views/workload_management/WorkloadManagementPageContainer';

const WorkloadManagementPageRouter = BaseRouter.extend({
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.setPageTitle(_('Workload Management').t());

        this.STATUS_POLLING_DELAY = 2000;
        this.enableAppBar = false;
        this.fetchAppLocals = true;
        this.fetchServerInfo = true;

        this.fetchContent();
    },

    startStatusPolling() {
        this.collection.status.startPolling({
            delay: this.STATUS_POLLING_DELAY,
            uiInactivity: true,
            stopOnError: false,
            data: {},
        });
    },

    fetchContent() {
        const self = this;
        this.model.enable = new Enable();
        this.model.disable = new Disable();
        this.collection.category = new Category();
        this.collection.pools = new Pools();
        this.collection.rules = new Rules();
        this.collection.status = new Status();
        this.collection.checks = new Checks();
        this.deferreds.status = this.collection.status.fetch();
        this.deferreds.checks = $.Deferred();
        this.collection.checks.fetch({
            success() {
                self.deferreds.checks.resolve();
            },
            error() {
                self.deferreds.checks.resolve();
            },
        });
        this.deferreds.category = $.Deferred();
        this.deferreds.pools = $.Deferred();
        this.deferreds.rules = $.Deferred();
        this.collection.category.fetch({
            success() {
                self.deferreds.category.resolve();
            },
            error() {
                self.deferreds.category.resolve();
            },
        });
        this.collection.pools.fetch({
            success() {
                self.deferreds.pools.resolve();
            },
            error() {
                self.deferreds.pools.resolve();
            },
        });
        this.collection.rules.fetch({
            success() {
                self.deferreds.rules.resolve();
            },
            error() {
                self.deferreds.rules.resolve();
            },
        });
    },

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);

        $.when(
            this.deferreds.pageViewRendered,
            this.deferreds.checks,
            this.deferreds.status,
            this.deferreds.category,
            this.deferreds.pools,
            this.deferreds.rules,
        ).done(() => {
            $('.preload').replaceWith(this.pageView.el);

            // this.model.user is fetched in routers/base.js
            const props = {
                category: this.collection.category,
                pools: this.collection.pools,
                rules: this.collection.rules,
                status: this.collection.status,
                checks: this.collection.checks,
                enable: this.model.enable,
                disable: this.model.disable,
                user: this.model.user,
            };

            render(
                <ThemeProvider theme={getReactUITheme()}>
                    <WorkloadManagementPageContainer {...props} />
                </ThemeProvider>,
                this.pageView.$('.main-section-body').get(0),
            );

            this.startStatusPolling();
        });
    },
});

export default WorkloadManagementPageRouter;
