import React from 'react'; // eslint-disable-line no-unused-vars
import $ from 'jquery';
import { render } from 'react-dom';
import { createTestHook } from '@splunk/base-lister/utils/TestSupport';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { _ } from '@splunk/ui-utils/i18n';
import BaseRouter from 'routers/Base';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import HealthReportManager from 'views/health_manager/HealthReportManager';

class HealthManagerRouter extends BaseRouter {
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.enableAppBar = false;

        this.setPageTitle(_('Health Report Features'));
    }

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);
        this.deferreds.pageViewRendered.then(() => {
            $('.preload').replaceWith(this.pageView.el);

            const props = {
                objectsCollectionPath: createRESTURL('/services/server/health-config'),
                permissions: {
                    read: true,
                    write: true,
                    canChangeStatus: true,
                    canCreate: false,
                    canClone: false,
                    canEditPermissions: false,
                    canEditTitleAndDescription: false,
                    canBulkChangeStatus: false,
                    canBulkEditPermissions: false,
                },
            };

            render(
                <ThemeProvider theme={getReactUITheme()}>
                    <HealthReportManager {...props} {...createTestHook(__filename)} />
                </ThemeProvider>,
                document.getElementsByClassName('main-section-body')[0],
            );
        });
    }
}

export default HealthManagerRouter;
