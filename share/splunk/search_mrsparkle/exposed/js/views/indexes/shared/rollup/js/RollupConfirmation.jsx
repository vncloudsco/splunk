import React from 'react';
import PropTypes from 'prop-types';
import css from 'views/indexes/shared/rollup/RollupConfirmation.pcssm';
import _ from 'underscore';

const RollupConfirmation = (props) => {
    const { isEdit } = props;
    const editDeletePrefix = isEdit ? _('Editing').t() : _('Deleting').t();
    const bodyText = `${editDeletePrefix} ${_('the policy does not affect the previously summarized data.').t()}`;
    return (
        <div>
            <span>{bodyText}</span>
            <a
                className={`${css.learnMore} external`}
                rel="noopener noreferrer"
                target="_blank"
                href="/help?location=settings.metrics.rollup"
            >{_('Learn more').t()}</a>
        </div>
    );
};

RollupConfirmation.propTypes = {
    isEdit: PropTypes.bool,
};

RollupConfirmation.defaultProps = {
    isEdit: false,
};

export default RollupConfirmation;
