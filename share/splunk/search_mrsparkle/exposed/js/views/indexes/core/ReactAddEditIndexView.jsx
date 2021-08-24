/* eslint react/forbid-prop-types: 0 */

import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import AddEditIndexView from 'views/indexes/core/AddEditIndexView';

class ReactAddEditIndexView extends BackboneAdapterBase {
    getView() {
        return new AddEditIndexView({
            model: {
                content: this.props.model.content,
                rollup: this.props.model.rollup,
                entity: this.props.model.entity,
                addEditIndexModel: this.props.model.addEditIndexModel,
                user: this.props.model.user,
                application: this.props.model.application,
            },
            collection: {
                appLocals: this.props.collection.appLocals,
                dimensions: this.props.collection.dimensions,
                metrics: this.props.collection.metrics,
                indexes: this.props.collection.indexes,
            },
        });
    }
}

ReactAddEditIndexView.propTypes = {
    model: PropTypes.object.isRequired,
    collection: PropTypes.object.isRequired,
};

export default ReactAddEditIndexView;
