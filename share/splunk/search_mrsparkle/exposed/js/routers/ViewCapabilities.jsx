import { _ } from '@splunk/ui-utils/i18n';
import $ from 'jquery';
import Backbone from 'backbone';
import React from 'react';
import { render } from 'react-dom';
import BaseRouter from 'routers/Base';
import route from 'uri/route';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import ErrorView from 'views/error/Master';
import Heading from '@splunk/react-ui/Heading';
import Link from '@splunk/react-ui/Link';
import ViewCapabilities from '@splunk/view-capabilities';

const ViewCapabilitiesRouter = BaseRouter.extend({
    routes: {
        ':locale/manager/:app/auth/view_capabilities?users=:userList': 'pageUsers',
        ':locale/manager/:app/auth/view_capabilities?roles=:roleList': 'pageRoles',
        '*root/:locale/manager/:app/auth/view_capabilities?users=:userList': 'pageRootedUsers',
        '*root/:locale/manager/:app/auth/view_capabilities?roles=:roleList': 'pageRootedRoles',
        '*splat': 'notSupported',
    },

    i18nStrings: {
        error: {
            status: _('404 Not Found'),
            message: _('Page not found!'),
        },
        accessControl: _('Access Control'),
        roles: _('Roles'),
        users: _('Users'),
        viewCapabilities: _('View Capabilities'),
    },

    cssStyles: {
        headerSection: {
            position: 'relative',
            padding: '20px 0 10px',
            margin: '0 20px',
            borderBottom: '1px solid #C3CBD4',
        },

        headerText: {
            margin: '0 0 10px 0',
        },

        tableSection: {
            marginLeft: 'auto',
            marginRight: 'auto',
            textAlign: 'center',
        },
    },

    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.enableAppBar = false;
    },

    pageUsers(locale, app, userList) {
        this.page(locale, app, 'users', userList);
    },

    pageRoles(locale, app, roleList) {
        this.page(locale, app, 'roles', roleList);
    },

    pageRootedUsers(root, locale, app, userList) {
        this.setRoot(root);
        this.pageUsers(locale, app, userList);
    },

    pageRootedRoles(root, locale, app, roleList) {
        this.setRoot(root);
        this.pageRoles(locale, app, roleList);
    },

    notSupported() {
        // Only reachable via manual change of the URL automatically generated from Users/Roles list pages.
        // For consistency with other pages, an invalid URL typed by the user will display the 'Oops' page.

        window.document.title = this.i18nStrings.error.status;

        const errorView = new ErrorView({
            model: {
                application: this.model.application,
                error: new Backbone.Model({
                    status: this.i18nStrings.error.status,
                    message: this.i18nStrings.error.message,
                }),
            },
        });

        $('#placeholder-main-section-body').append(errorView.render().el);
    },

    page(locale, app, entityType, entity) {
        BaseRouter.prototype.page.apply(this, arguments); // eslint-disable-line prefer-rest-params
        this.setPageTitle(this.i18nStrings.viewCapabilities);

        const pageElements = [];

        pageElements.push(
            <div style={this.cssStyles.headerSection}>
                <Heading level={1} style={this.cssStyles.headerText}>{this.i18nStrings.viewCapabilities}</Heading>
                {this.getBreadCrumbDiv(entityType, entity)}
            </div>,
        );

        $.when(this.deferreds.pageViewRendered).then(() => {
            $('.preload').replaceWith(this.pageView.el);

            const props = {
                entityType,
                entity,
            };

            pageElements.push(<div style={this.cssStyles.tableSection}><ViewCapabilities {...props} /></div>);

            render(
                <ThemeProvider theme={getReactUITheme()}>
                    <React.Fragment>{pageElements}</React.Fragment>
                </ThemeProvider>,
                this.pageView.$('.main-section-body').get(0),
            );
        });
    },

    setRoot(root) {
        this.model.application.set(
            {
                root,
            },
            {
                silent: true,
            },
        );
    },

    getBreadCrumbDiv(entityType, entity) {
        const breadCrumbHelper = {
            // Combination of leading and trailing space with '>>' in between
            separator: ` ${String.fromCharCode(187)} `,

            urlBase: [
                this.model.application.get('root'),
                this.model.application.get('locale'),
                this.model.application.get('app'),
            ],
        };

        const breadCrumbContent = [];

        switch (entityType) {
            case 'roles': {
                breadCrumbContent.push(
                    <Link to={route.manager(...breadCrumbHelper.urlBase, ['authorization', 'roles'])}>
                        {this.i18nStrings.roles}
                    </Link>,
                );

                breadCrumbContent.push(breadCrumbHelper.separator);

                break;
            }

            case 'users': {
                breadCrumbContent.push(
                    <Link to={route.manager(...breadCrumbHelper.urlBase, ['authentication', 'users'])}>
                        {this.i18nStrings.users}
                    </Link>,
                );

                breadCrumbContent.push(breadCrumbHelper.separator);

                break;
            }

            default: {
                // This should never occur
                // Do Nothing
            }
        }

        breadCrumbContent.push(entity);

        return <div>{breadCrumbContent}</div>;
    },
});

export default ViewCapabilitiesRouter;
