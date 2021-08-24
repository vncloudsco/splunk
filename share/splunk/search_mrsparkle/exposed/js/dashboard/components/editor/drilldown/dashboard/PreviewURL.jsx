import _ from 'underscore';
import PropTypes from 'prop-types';
import React from 'react';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import { createTestHook } from 'util/test_support';
import css from './PreviewURL.pcssm';

const PreviewURL = ({
    url,
}) => {
    const label = _.isString(url) ? url : url.label;
    const value = _.isString(url) ? url : url.value;

    // show PreviewURL only when the url is not an empty string.
    if (!value) {
        return null;
    }

    return (
        <ControlGroup
            label={_('Preview URL').t()}
            controlsLayout="none"
            {...createTestHook(module.id, 'PreviewURL')}
        >
            <div className={css.padTopBottom} data-test="preview-url">
                <span className={css.linkLabel}>{label}</span>
            </div>
        </ControlGroup>
    );
};

PreviewURL.propTypes = {
    url: PropTypes.oneOfType([
        // sometimes the label and actual value are not the same.
        PropTypes.shape({
            label: PropTypes.string.isRequired,
            value: PropTypes.string.isRequired,
        }),
        PropTypes.string,
    ]).isRequired,
};

export default PreviewURL;
