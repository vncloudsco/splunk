import React, { Component } from 'react';
import { _ } from '@splunk/ui-utils/i18n';
import Button from '@splunk/react-ui/Button';
import Heading from '@splunk/react-ui/Heading';
import P from '@splunk/react-ui/Paragraph';
import Link from '@splunk/react-ui/Link';
import PropTypes from 'prop-types';
import TokenActions from 'views/tokens/table/columns/TokenActions';
import CreateToken from 'views/tokens/modals/CreateToken';
import { formatLastUsedTime, formatTokenExp, formatTimestamp,
    getToggleTokenAuthURL, MAX_FILTER_LENGTH } from 'views/tokens/Utils';
import 'views/tokens/Tokens.pcss';
import TokensDisabled from 'views/tokens/TokensDisabled';
import TokenSettingsModal from 'views/tokens/modals/TokenSettings';
import TokensMain from './TokensMain';

class TokensManager extends Component {

    static propTypes = {
        callToggleTokenAuth: PropTypes.func.isRequired,
        getTokenAuth: PropTypes.func.isRequired,
        tokenAuthEnabled: PropTypes.bool.isRequired,
        defaultExpiration: PropTypes.string,
        learnMoreLink: PropTypes.string.isRequired,
        canViewTokens: PropTypes.bool.isRequired,
        objectNameSingular: PropTypes.string,
        permissions: PropTypes.shape({
            editSettings: PropTypes.bool.isRequired,
        }).isRequired,
    };

    static defaultProps = {
        showAppColumn: false,
        showOwnerColumn: false,
        showAppFilter: false,
        showOwnerFilter: false,
        showSharingColumn: false,
        hasRowExpansion: true,
        objectNamePlural: _('Tokens'),
        objectNameSingular: _('Token'),
        ColumnActions: TokenActions,
        ModalNew: CreateToken,
        customColumns: [
            {
                key: 'usernameCol',
                sortKey: 'claims.sub',
                label: _('Username'),
                content: object => object.content.claims.sub,
            },
            {
                key: 'audienceCol',
                sortKey: 'claims.aud',
                label: _('Audience'),
                content: object => object.content.claims.aud,
            },
            {
                key: 'issuedAtCol',
                sortKey: 'claims.iat',
                label: _('Issued At'),
                content: object => formatTimestamp(object.content.claims.iat),
            },
            {
                key: 'expirationCol',
                sortKey: 'claims.exp',
                label: _('Expiration'),
                content: object => formatTokenExp(object.content.claims.exp),
            },
            {
                key: 'lastUsed',
                sortKey: 'lastUsed',
                label: _('Last Used'),
                content: object => formatLastUsedTime(object.content.lastUsed),
            },
        ],
        defaultExpiration: '',

        /**
         * Overrriding the default method returning the fetch collection data.
         * Add conditional to check for listAll capability to build args for GET
         * @param {Object} state current state of the component
         * @param {Object} newData data that is being passed to handleRefreshListing but not
         * yet saved in the state.
         * @returns {Object} an object containing the fetch data necessary for the collection fetch.
         */
        getObjectsCollectionFetchData(state, newData) {
            const fetchArgs = {
                count: state.countPerPage,
                sort_key: state.sortKey,
                sort_dir: state.sortDirection,
                offset: state.offset,
                search: state.filterString ? state.filterString.substring(0, MAX_FILTER_LENGTH) : null,
                output_mode: 'json',
            };
            if (!this.permissions.listAll && !this.permissions.editAll) {
                fetchArgs.username = this.username;
            }
            const data = Object.assign(
                {},
                fetchArgs,
                newData);
            delete data.filterString;
            return data;
        },
    };

    constructor(props, context) {
        super(props, context);
        this.state = {
            /** Boolean indicating whether or not disableTokenAuth Modal is open */
            tokenSettingsModalOpen: false,
            /** Boolean indicating whether the page is working (saving, deleting, ...). Used to disable button. */
            isWorking: false,
            /** Boolean indicating whether or not tokenAuth is enabled */
            tokenAuthEnabled: this.props.tokenAuthEnabled,
            defaultExpiration: this.props.defaultExpiration,
        };
    }

    /**
     * Set token auth status to hide or show token grid
     */
    setTokenSettings = (disabled, expiration) => {
        this.setState({
            isWorking: false,
            tokenAuthEnabled: !disabled,
            defaultExpiration: expiration,
        });
    };

    /**
     * Handle disabling of Tokens from Tokens Manager page. On success, close modal and set
     * state tokenAuthEnabled to opposite of previous value
     */
    handleToggleTokenAuth = () => {
        this.setState({ isWorking: true });
        this.props.callToggleTokenAuth(getToggleTokenAuthURL(this.state.tokenAuthEnabled)).then(() => {
            // Close disableTokenAuth modal, set isWorking to false, and
            // inverse the tokenAuthEnabled state to re-render the correct view
            this.setState(state => ({
                isWorking: false,
                disableTokenAuthOpen: false,
                errorMessage: '',
                tokenAuthEnabled: !state.tokenAuthEnabled,
            }));
        }, response => this.setState({ isWorking: false, errorMessage: response.message }));
    }

    /**
     * Set tokenSettingsModalOpen to true on the state to track token settings modal is open.
     */
    openTokenSettingsModal = () => {
        this.setState({ tokenSettingsModalOpen: true });
    }

    /**
     * Set tokenSettingsModalOpen to false on the state to track token settings modal is closed.
     */
    handleTokenSettingsModalClose = () => {
        this.setState({
            isWorking: false,
            tokenSettingsModalOpen: false,
            errorMessage: '',
        });
    };

    checkTokenAuth = () => {
        this.props.getTokenAuth().then((response) => {
            const disabled = response.entry[0].content.disabled;
            this.setState({
                tokenAuthEnabled: !disabled,
            });
        });
    };

    render() {
        const bStyleLeft = {
            margin: '0 20px 0 20px',
            position: 'absolute',
            top: '155px',
        };
        const bStyleRight = {
            float: 'right',
            top: '20px',
            margin: '0 20px 0 10px',
        };

        return (
            this.state.tokenAuthEnabled ? (
                <div data-test-name="TokensManagerPage">
                    {this.props.permissions.editSettings &&
                          (<div>
                              <Button
                                  style={this.props.canViewTokens ? bStyleRight : bStyleLeft}
                                  label={_('Token Settings')}
                                  onClick={this.openTokenSettingsModal}
                                  data-test-name="TokenSettingsBtn"
                              />
                              {this.state.tokenSettingsModalOpen &&
                              (<TokenSettingsModal
                                  objectNameSingular={this.props.objectNameSingular}
                                  open={this.state.tokenSettingsModalOpen}
                                  handleRequestClose={this.handleTokenSettingsModalClose}
                                  setTokenSettings={this.setTokenSettings}
                                  tokenAuthEnabled={this.state.tokenAuthEnabled}
                                  defaultExpiration={this.state.defaultExpiration}
                                  callToggleTokenAuth={this.props.callToggleTokenAuth}
                              />)
                              }
                          </div>)
                    }
                    { this.props.canViewTokens ?
                        (<TokensMain checkTokenAuth={this.checkTokenAuth} {...this.props} />) :
                        (<div
                            style={{ padding: '20px 20px 0', maxWidth: '600px', display: 'block' }}
                            data-test-name="TokensManagerPage.editTokensSettingsOnly"
                        >
                            <Heading
                                level={1}
                                style={{ margin: '0 0 10px 0', lineHeight: '24px' }}
                                data-test-name="TokensManagerPage.Heading"
                            >
                                {_('Token authentication is currently enabled')}
                            </Heading>
                            <P data-test-name="TokensManagerPage.Paragraph">
                                {_('You don\'t have permission to manage individual tokens on this ' +
                                'instance, but there might be enabled tokens. If you click "Disable ' +
                                'Token Authentication", all currently enabled tokens are disabled. ' +
                                'If you need to manage individual tokens, contact your administrator. ')}
                                <Link
                                    to={this.props.learnMoreLink}
                                    data-test-name="TokensManagerPage.learnMoreLink"
                                    openInNewContext
                                >
                                    {_('Learn More')}
                                </Link>
                            </P>
                        </div>)
                    }
                </div>
            ) : (<TokensDisabled handleToggleTokenAuth={this.handleToggleTokenAuth} {...this.props} />)
        );
    }
}

export default TokensManager;
