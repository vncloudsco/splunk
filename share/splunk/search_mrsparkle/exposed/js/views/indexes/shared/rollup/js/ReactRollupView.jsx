import BackboneAdapterBase from 'components/BackboneAdapterBase';
import RollupView from 'views/indexes/shared/rollup/js/RollupView';

class ReactRollupView extends BackboneAdapterBase {
    getView() {
        return new RollupView({
            model: {
                content: this.props.model.content,
                rollup: this.props.model.rollup,
            },
            collection: {
                dimensions: this.props.collection.dimensions,
                metrics: this.props.collection.metrics,
                indexes: this.props.collection.indexes,
            },
        });
    }
}

export default ReactRollupView;
