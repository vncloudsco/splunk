/* eslint react/forbid-prop-types: 0 */

import PropTypes from 'prop-types';
import Backbone from 'backbone';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import BackboneAccumulatorControl from 'views/shared/controls/AccumulatorControl';

class SearchInput extends BackboneAdapterBase {
    getView() {
        return new BackboneAccumulatorControl({
            modelAttribute: this.props.modelattribute,
            model: this.props.model,
            availableItems: this.props.availableitems,
            selectedItems: this.props.selecteditems,
        });
    }
}

SearchInput.propTypes = {
    modelattribute: PropTypes.string.isRequired,
    model: PropTypes.instanceOf(Backbone.Model).isRequired,
    availableitems: PropTypes.array.isRequired,
    selecteditems: PropTypes.array.isRequired,
};

export default SearchInput;
