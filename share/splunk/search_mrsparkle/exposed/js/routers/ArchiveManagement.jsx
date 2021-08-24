import _ from 'underscore';
import $ from 'jquery';
import React from 'react';
import { render } from 'react-dom';
import ErrorView from 'views/shared/react/Error';
import BaseRouter from 'routers/Base';
import querystring from 'querystring';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import ArchiveManagementMaster from 'views/archive_management/ArchiveManagement';

const ArchiveManagementRouter = BaseRouter.extend({
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.setPageTitle(_('Archive Management').t());
        this.enableAppBar = false;
        this.fetchAppLocals = true;
        this.fetchServerInfo = true;
    },

    fetchRestoreHistory(data) {
        return fetch(createRESTURL('restore_history_sh'), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to process restore history.').t()));
    },

    fetchArchiveMetadata(data) {
        return fetch(createRESTURL('index_restore_sh'), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to fetch archive metadata.').t()));
    },

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);

        const props = {
            onFetchHistory: this.fetchRestoreHistory,
            onFetchArchive: this.fetchArchiveMetadata,
        };
        $.when(this.deferreds.pageViewRendered,
            this.deferreds.appLocals, this.deferreds.serverInfo).done(() => {
                $('.preload').replaceWith(this.pageView.el);
                if (this.collection.appLocals.isArchiverAppInstalled()) {
                    // render the contents only on S2 stacks
                    render(
                        <ThemeProvider theme={getReactUITheme()}>
                            <ArchiveManagementMaster {...props} />
                        </ThemeProvider>,
                        this.pageView.$('.main-section-body').get(0),
                    );
                } else {
                    const eProps = {
                        model: {
                            application: this.model.application,
                            serverInfo: this.model.serverInfo,
                        },
                        message: _('You do not have permission to view the contents of this page. ' +
                                'Contact Splunk support to learn more.').t(),
                    };
                    render(
                        <ThemeProvider theme={getReactUITheme()}>
                            <ErrorView {...eProps} />
                        </ThemeProvider>,
                        this.pageView.$('.main-section-body').get(0),
                    );
                }
            });
    },
});

export default ArchiveManagementRouter;
