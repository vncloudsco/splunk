/* eslint react/forbid-prop-types: 0 */

import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import BackboneFlashMessages from 'views/shared/FlashMessages';

class FlashMessages extends BackboneAdapterBase {
    getView() {
        return new BackboneFlashMessages({
            model: this.props.model,
        });
    }
}

FlashMessages.propTypes = {
    model: PropTypes.object.isRequired,
};

export default FlashMessages;
