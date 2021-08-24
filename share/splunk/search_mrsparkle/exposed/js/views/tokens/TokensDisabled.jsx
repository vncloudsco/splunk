import React from 'react';
import PropTypes from 'prop-types';
import Heading from '@splunk/react-ui/Heading';
import Button from '@splunk/react-ui/Button';
import P from '@splunk/react-ui/Paragraph';
import Link from '@splunk/react-ui/Link';
import { _ } from '@splunk/ui-utils/i18n';

/**
 * TokensDisabled Component to display when TokenAuth is disabled
*/
const TokensDisabled = props => (
    <div style={{ padding: '20px 20px 0' }} data-test-name="TokensDisabledPage">
        <Heading
            level={1}
            style={{ margin: '0 0 10px 0' }}
            data-test-name="TokensDisabledPage.heading"
        >
            {_('Token authentication is currently disabled')}
        </Heading>
        <div>
            <P data-test-name="TokensDisabledPage.paragraph">
                {props.permissions.editSettings ?
                    _('Click "Enable Token Authentication" to enable token authentication. ')
                    : _('You don\'t have permission to make changes to token authentication' +
                    ' settings. Contact your administrator and have them assign you a role that has this' +
                    ' capability. ')
                }
                <Link to={props.learnMoreLink} openInNewContext data-test-name="TokensDisabledPage.learnMoreLink">
                    {_('Learn More')}
                </Link>
            </P>
            {props.permissions.editSettings &&
                <Button
                    label={_('Enable Token Authentication')}
                    appearance="primary"
                    onClick={props.handleToggleTokenAuth}
                    data-test-name="TokensDisabledPage.enableBtn"
                />
            }
        </div>
    </div>
);

TokensDisabled.propTypes = {
    handleToggleTokenAuth: PropTypes.func.isRequired,
    learnMoreLink: PropTypes.string.isRequired,
    permissions: PropTypes.shape({
        editSettings: PropTypes.bool.isRequired,
    }).isRequired,
};
export default TokensDisabled;