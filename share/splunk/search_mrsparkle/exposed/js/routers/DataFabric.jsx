import _ from 'underscore';
import $ from 'jquery';
import React from 'react';
import { render } from 'react-dom';
import FederationsCollection from 'collections/services/dfs/Federations';
import FshRolesCollection from 'collections/services/authorization/FshRoles';
import BaseRouter from 'routers/Base';
import DataFabricContainer from 'views/data_fabric/DataFabricContainer';
import LicensePage from 'views/data_fabric/LicensePage';

const DataFabricRouter = BaseRouter.extend({
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.setPageTitle(_('Data Fabric').t());

        this.STATUS_POLLING_DELAY = 2000;
        this.enableAppBar = false;
        this.fetchAppLocals = true;
        this.fetchServerInfo = true;

        // collections
        this.collection.federations = new FederationsCollection();
        this.collection.fshRoles = new FshRolesCollection();

        // deferreds
        this.deferreds.federations = $.Deferred();
        this.deferreds.fshRoles = $.Deferred();
    },

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);

        $.when(
            this.deferreds.dfsEnable,
            this.deferreds.pageViewRendered,
            this.deferreds.serverInfo,
        ).then(() => {
            $('.preload').replaceWith(this.pageView.el);
            render(<LicensePage status="loading" />, this.pageView.$('.main-section-body').get(0));
            if (!this.model.serverInfo.isDFSEnabled()) {
                render(<LicensePage status="success" />, this.pageView.$('.main-section-body').get(0));
            } else {
                this.bootstrapFederations();
                this.bootstrapFshRoles();
                $.when(this.deferreds.federations, this.deferreds.fshRoles).then(() => {
                    const props = {
                        collection: {
                            federations: this.collection.federations,
                            fshRoles: this.collection.fshRoles,
                        },
                    };
                    render(<DataFabricContainer {...props} />, this.pageView.$('.main-section-body').get(0));
                });
            }
        });
    },

    bootstrapFederations() {
        if (this.deferreds.federations.state() !== 'resolved') {
            this.collection.federations.fetch({
                data: { count: 0 },
                success: () => {
                    this.deferreds.federations.resolve();
                },
                error: () => {
                    this.deferreds.federations.resolve();
                },
            });
        }
    },

    bootstrapFshRoles() {
        if (this.deferreds.fshRoles.state() !== 'resolved') {
            this.collection.fshRoles.fetch({
                fshSearch: true,
                data: { count: 0 },
                success: () => {
                    this.deferreds.fshRoles.resolve();
                },
                error: () => {
                    this.deferreds.fshRoles.resolve();
                },
            });
        }
    },
});

export default DataFabricRouter;
