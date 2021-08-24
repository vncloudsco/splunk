import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import Text from '@splunk/react-ui/Text';
import OpenInNewTab from 'dashboard/components/shared/OpenInNewTab';
import FormMessage from 'dashboard/components/shared/FormMessage';
import { createTestHook } from 'util/test_support';

const UrlActionEditor = ({
    url,
    urlError,
    onUrlChange,
    target,
    onTargetChange,
}) => {
    const label = _('URL').t();
    const hasError = !!urlError;
    const errorMessage = hasError ? `${label} ${urlError}` : '';
    return (
        <div {...createTestHook(module.id)}>
            <FormMessage active={hasError} type="error" message={errorMessage} />
            <ControlGroup
                label={label}
                error={hasError}
                help={_('Use a relative URL or absolute URL, for example, ' +
                    '/app/search/datasets, or https://www.splunk.com').t()}
            >
                <Text
                    value={url}
                    onChange={onUrlChange}
                    multiline
                    placeholder=""
                    error={hasError}
                />
            </ControlGroup>
            <OpenInNewTab
                value={target}
                onClick={onTargetChange}
            />
        </div>
    );
};

UrlActionEditor.propTypes = {
    url: PropTypes.string,
    urlError: PropTypes.string,
    onUrlChange: PropTypes.func.isRequired,
    target: PropTypes.string.isRequired,
    onTargetChange: PropTypes.func.isRequired,
};

UrlActionEditor.defaultProps = {
    urlError: '',
    url: '',
};

export default UrlActionEditor;
