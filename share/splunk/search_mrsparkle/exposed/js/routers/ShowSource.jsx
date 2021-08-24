import { _ } from 'underscore';
import $ from 'jquery';
import React from 'react';
import { render } from 'react-dom';
import BaseRouter from 'routers/Base';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import classicurlModel from 'models/classicurl';
import JobResultModel from 'models/services/search/jobs/Result';
import ShowSource from 'views/show_source';
import splunkdUtils from 'util/splunkd_utils';

const ShowSourceRouter = BaseRouter.extend({
    routes: {
        ':locale/app/:app/show_source*splat': 'showSource',
        '*root/:locale/app/:app/show_source*splat': 'showSource',
    },

    i18nStrings: {
        error: {
            status: _('404 Not Found').t(),
            message: _('Page not found!').t(),
        },
        noContent: _('No content available.').t(),
        noSid: _('No sid was specified.').t(),
        heading: _('Show Source').t(),
    },

    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.enableAppBar = false;
        this.model.jobResultModel = new JobResultModel();
        this.deferreds.searchJobDeferred = $.Deferred();
    },
    showSource(locale, app) {
        BaseRouter.prototype.page.apply(this, [locale, app, 'show_source']); // eslint-disable-line prefer-rest-params
        this.setPageTitle(this.i18nStrings.heading);

        const data = {
            field_list: '_raw,target,MSG_TYPE,MSG_CONTENT,_decoration',
            surrounding: '1',
            mode: 'events',
            offset: classicurlModel.get('offset') || 0,
            latest_time: classicurlModel.get('latest_time') || 0,
            count: 500,
            max_lines: classicurlModel.get('max_lines_constraint') || 500,
        };
        classicurlModel.fetch({
            success: () => {
                if (classicurlModel.get('sid')) {
                    this.model.jobResultModel.set('id', `/services/search/jobs/${classicurlModel.get('sid')}/events`);
                    this.model.jobResultModel.fetch({
                        data,
                        success: () => this.deferreds.searchJobDeferred.resolve(),
                        error: (model, response) => {
                            this.model.jobResultModel.unset('id');
                            this.deferreds.searchJobDeferred.resolve(response);
                        },
                    });
                } else {
                    const noSidError = splunkdUtils.createSplunkDMessage(splunkdUtils.FATAL,
                                        this.i18nStrings.noSid);
                    this.model.jobResultModel.trigger('error', this.model.jobResultModel, noSidError);
                    this.deferreds.searchJobDeferred.resolve();
                }
            },
        });

        $.when(this.deferreds.pageViewRendered, this.deferreds.searchJobDeferred).then((...thenResult) => {
            $('.preload').replaceWith(this.pageView.el);

            const props = {
                textStrings: this.i18nStrings,
                events: this.model.jobResultModel.results.models.map(event => ({ value: event.getRawText(),
                    isTarget: !!event.get('target'),
                    isGap: event.get('_decoration') === 'showsourceGap',
                    isInValid: event.get('_decoration') === 'showsourceInvalid',
                    MSG_CONTENT: event.get('MSG_CONTENT'),
                })),
                error: thenResult[1],
                data,
                count: classicurlModel.get('count') || 50,
            };

            render(
                <ThemeProvider theme={getReactUITheme()}>
                    <ShowSource {...props} />
                </ThemeProvider>,
                this.pageView.$('.main-section-body').get(0),
            );
        });
    },

});

export default ShowSourceRouter;
