import 'core-js';
import React from 'react'; // eslint-disable-line no-unused-vars
import $ from 'jquery';
import { render } from 'react-dom';
import BaseRouter from 'routers/Base';
import { _ } from '@splunk/ui-utils/i18n';
import IndexesCollection from 'collections/services/data/Indexes';
import ClusterConfigModel from 'models/services/cluster/Config';
import HealthDetailsModel from 'models/services/server/HealthDetails';
import Bookmarks from 'splunk_monitoring_console/collections/Bookmarks';
import Metrics from 'splunk_monitoring_console/collections/Metrics';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import Landing from 'splunk_monitoring_console/views/landing/Landing';

class MonitoringConsoleLandingRouter extends BaseRouter {
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.setPageTitle(_('Summary'));
        this.fetchContent();
    }

    fetchContent() {
        // Health Details - For Anomalies Tabel + Deployment Components
        this.model.healthDetails = new HealthDetailsModel();
        this.model.healthDetails.set({ id: 'details' });
        this.deferreds.healthDetails = this.model.healthDetails.fetch();

        // Indexer Cluster Config - For Deployment Topology
        this.model.indexerClustering = new ClusterConfigModel();
        this.deferreds.indexerClustering = this.model.indexerClustering.fetch();

        // Bookmarks Collection - For Bookmark Component
        this.collection.bookmarks = new Bookmarks();
        this.deferreds.bookmarks = this.collection.bookmarks.fetch();

        // MC Metrics - For Deployment Metrics
        this.collection.metrics = new Metrics();
        this.deferreds.metrics = this.collection.metrics.fetch();

        // Indexes - For Deployment Metrics
        this.collection.indexes = new IndexesCollection();
        this.deferreds.indexes = this.collection.indexes.fetch();
    }

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);
        $.when(
            this.deferreds.pageViewRendered,
            this.deferreds.application,
            this.deferreds.healthDetails,
            this.deferreds.indexerClustering,
            this.deferreds.bookmarks,
            this.deferreds.metrics,
            this.deferreds.indexes,
        ).done(() => {
            $('.preload').replaceWith(this.pageView.el);
            const props = {
                appLocal: this.model.appLocal,
                application: this.model.application,
                serverInfo: this.model.serverInfo,
                healthDetails: this.model.healthDetails,
                indexerClustering: this.model.indexerClustering,
                bookmarks: this.collection.bookmarks,
                metrics: this.collection.metrics,
                indexes: this.collection.indexes.models.length,
            };

            render(
                <ThemeProvider theme={getReactUITheme()}>
                    <Landing {...props} />
                </ThemeProvider>,
                document.getElementsByClassName('main-section-body')[0],
            );
        });
    }
}

export default MonitoringConsoleLandingRouter;
