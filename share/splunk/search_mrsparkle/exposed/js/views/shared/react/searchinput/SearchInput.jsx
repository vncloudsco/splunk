/* eslint react/forbid-prop-types: 0 */

import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import BackboneSearchInput from 'views/shared/searchbarinput/Master';

class SearchInput extends BackboneAdapterBase {
    getView() {
        return new BackboneSearchInput({
            model: {
                user: this.props.model.user,
                content: this.props.model.content,
                application: this.props.model.application,
                searchAttribute: this.props.searchAttribute,
                searchAssistant: this.props.searchAssistant,
            },
            collection: {
                searchBNFs: this.props.collection.searchBNFs,
            },
        });
    }
}

SearchInput.propTypes = {
    model: PropTypes.object.isRequired,
    collection: PropTypes.object.isRequired,
};

export default SearchInput;
