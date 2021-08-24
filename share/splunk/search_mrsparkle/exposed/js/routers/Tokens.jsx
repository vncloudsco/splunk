import React from 'react';
import $ from 'jquery';
import { render } from 'react-dom';
import { _ } from '@splunk/ui-utils/i18n';
import BaseRouter from 'routers/Base';
import { createRESTURL } from '@splunk/splunk-utils/url';
import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import TokensManager from 'views/tokens/Tokens';
import Table from '@splunk/react-ui/Table';
import DefinitionList from '@splunk/react-ui/DefinitionList';
import querystring from 'querystring';
import { getTokenPermissions, formatTimestamp, formatLastUsedIp, getTokenAuthSettingsURL,
  canViewTokens, TOKENS_COLLECTION_PATH } from 'views/tokens/Utils';
import { getReactUITheme, ThemeProvider } from 'util/theme_utils';
import route from 'uri/route';
import { normalizeBoolean } from '@splunk/ui-utils/boolean';

class TokensRouter extends BaseRouter {
    initialize(...args) {
        BaseRouter.prototype.initialize.call(this, ...args);
        this.enableAppBar = false;
        this.setPageTitle(_('Tokens'));
        this.deferreds.tokenAuth = $.Deferred();
    }

    /**
     * Call Token Auth endpoint to Get settings
     * @param url - REST endpoint url
     */
    getTokenAuth = () => (
        fetch(getTokenAuthSettingsURL(), {
            ...defaultFetchInit,
        })
        .then(handleResponse(200))
        .then((response) => {
            this.tokenAuth = response;
            this.deferreds.tokenAuth.resolve();
            return response;
        })
        .catch(handleError(_('Unable to fetch token authentication settings.')))
    )

    /**
     * Call Token Auth endpoint to Edit settings
     * @param url - REST endpoint url
     */
    callToggleTokenAuth = url => (
        fetch(url, {
            ...defaultFetchInit,
            method: 'POST',
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to change token status.')))
    );

    /**
     * Call Create token REST endpoint
     * @param url - REST endpoint url
     * @returns Promise
     */
    callCreateToken = data => (
        fetch(createRESTURL(TOKENS_COLLECTION_PATH), {
            ...defaultFetchInit,
            method: 'POST',
            body: querystring.encode(data),
        })
        .then(handleResponse(201))
        .catch(handleError(_('Unable to create token.')))
    );

    /**
     * Call Delete token REST endpoint
     * @param url - REST endpoint url
     * @returns Promise
     */
    callDeleteToken = url => (
        fetch(url, {
            ...defaultFetchInit,
            method: 'DELETE',
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to delete token.')))
    );

    /**
     * Call Change token status REST endpoint
     * @param url - REST endpoint url
     * @returns Promise
     */
    callChangeStatus = url => (
        fetch(url, {
            ...defaultFetchInit,
            method: 'POST',
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to change token status.')))
    );

    getExpansionRow = (object, colSpan) => (
        <Table.Row key={`expansion-row-${object.name}`}>
            <Table.Cell
                key={`expansion-cell-${object.name}`}
                style={{ borderTop: 'none' }}
                colSpan={colSpan}
            >
                <DefinitionList>
                    <DefinitionList.Term>{_('Token ID')}</DefinitionList.Term>
                    <DefinitionList.Description>
                        {object.name}
                    </DefinitionList.Description>
                    <DefinitionList.Term>{_('Issued By')}</DefinitionList.Term>
                    <DefinitionList.Description>
                        {object.content.claims.iss}
                    </DefinitionList.Description>
                    <DefinitionList.Term>{_('Not Before')}</DefinitionList.Term>
                    <DefinitionList.Description>
                        {formatTimestamp(object.content.claims.nbr)}
                    </DefinitionList.Description>
                    <DefinitionList.Term>{_('Identity Provider')}</DefinitionList.Term>
                    <DefinitionList.Description>
                        {object.content.claims.idp}
                    </DefinitionList.Description>
                    <DefinitionList.Term>{_('Last Used IP')}</DefinitionList.Term>
                    <DefinitionList.Description>
                        {formatLastUsedIp(object.content.lastUsedIp)}
                    </DefinitionList.Description>
                </DefinitionList>
            </Table.Cell>
        </Table.Row>
    );

    getProps = (model) => {
        // Set Permissions based on capabilities
        const capabilities = model.user.entry.content.get('capabilities');
        const permissions = getTokenPermissions(capabilities);
        const props = {
            objectsCollectionPath: TOKENS_COLLECTION_PATH,
            username: model.user.entry.get('name'),
            getTokenAuth: this.getTokenAuth,
            callCreateToken: this.callCreateToken,
            callDeleteToken: this.callDeleteToken,
            callChangeStatus: this.callChangeStatus,
            callToggleTokenAuth: this.callToggleTokenAuth,
            getExpansionRow: this.getExpansionRow,
            formatStatus: this.formatStatus,
            getEditUrl: () => null,
            isEnabled: object => object.content.status === 'enabled',
            showStatusColumn: true,
            showActionsColumn: capabilities.indexOf('edit_tokens_all') > -1 ||
                capabilities.indexOf('edit_tokens_own') > -1,
            tokenAuthEnabled: this.tokenAuth.entry && this.tokenAuth.entry[0] &&
                !normalizeBoolean(this.tokenAuth.entry[0].content.disabled),
            defaultExpiration: this.tokenAuth.entry && this.tokenAuth.entry[0] &&
                this.tokenAuth.entry[0].content.expiration,
            learnMoreLink: route.docHelp(
                this.model.application.get('root'),
                this.model.application.get('localed'),
                'learnmore.security.tokenauth',
            ),
            canViewTokens: canViewTokens(permissions),
            permissions,
        };

        return props;
    }

    page(...args) {
        this.getTokenAuth();
        BaseRouter.prototype.page.call(this, ...args);
        $.when(this.deferreds.pageViewRendered, this.deferreds.user,
            this.deferreds.serverInfo, this.deferreds.tokenAuth).done(() => {
                $('.preload').replaceWith(this.pageView.el);
                const props = this.getProps(this.model);
                render(
                    <ThemeProvider theme={getReactUITheme()}>
                        <TokensManager {...props} />
                    </ThemeProvider>,
                    $('.main-section-body')[0],
                );
            });
    }
}

export default TokensRouter;
