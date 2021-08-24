import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import Themes from './Themes';

class ThemesAdapter extends BackboneAdapterBase {
    getView() {
        return new Themes({
            model: this.context.model,
            collection: this.context.collection,
        }).activate({ deep: true });
    }
}

ThemesAdapter.contextTypes = {
    model: PropTypes.object.isRequired,
    collection: PropTypes.object.isRequired,
};

export default ThemesAdapter;