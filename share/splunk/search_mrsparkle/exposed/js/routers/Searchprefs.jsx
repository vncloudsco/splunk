import React from 'react'; // eslint-disable-line no-unused-vars
import $ from 'jquery';
import { render } from 'react-dom';
import { _ } from '@splunk/ui-utils/i18n';
import BaseRouter from 'routers/Base';
import SearchPrefs from 'views/SearchPrefs';
import ConcurrencySettings from 'models/shared/ConcurrencySettings';
import SearchConcurrency from 'models/shared/SearchConcurrency';

class SearchPrefsRouter extends BaseRouter {
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.enableAppBar = false;

        this.setPageTitle(_('Search Preferences'));
        this.fetchConcurrencyInfo();
    }

    fetchConcurrencyInfo() {
        this.model.concurrencySettings = new ConcurrencySettings();
        this.deferreds.concurrencySettings = this.model.concurrencySettings.fetch();
        this.model.searchConcurrency = new SearchConcurrency();
        this.deferreds.searchConcurrency = this.model.searchConcurrency.fetch();
    }

    page(...args) {
        BaseRouter.prototype.page.call(this, ...args);

        $.when(
            this.deferreds.pageViewRendered,
            this.deferreds.userPref,
            this.deferreds.concurrencySettings,
            this.deferreds.searchConcurrency,
        ).done(() => {
            $('.preload').replaceWith(this.pageView.el);
            const props = {
                userPrefs: this.model.userPref,
                application: this.model.application,
                concurrencySettings: this.model.concurrencySettings,
                searchConcurrency: this.model.searchConcurrency,
            };

            render(
                <SearchPrefs
                    {...props}
                />,
                document.getElementsByClassName('main-section-body')[0],
            );
        });
    }
}

export default SearchPrefsRouter;
