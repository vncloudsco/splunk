import PropTypes from 'prop-types';
import BackboneAdapterBase from 'components/BackboneAdapterBase';
import SearchControl from 'views/shared/controls/SearchTextareaControl';
import Backbone from 'backbone';
import ModelHelper from 'controllers/dashboard/helpers/ModelHelper';
import UserModel from 'models/services/authentication/User';
import { getSearchEditorTheme } from 'util/theme_utils';
import { createTestHook } from 'util/test_support';

class SearchEditor extends BackboneAdapterBase {
    constructor(props, context) {
        super(props, context);
        this.model = Object.assign({}, this.context.model, {
            content: new Backbone.Model(
                this.context.model.report.entry.content.toJSON()),
        });
        // set initial value
        this.model.content.set('search', props.value);
        this.collection = Object.assign(
            {},
            this.context.collection,
            {
                // searchBNFs fetching needs to be lazy and cached because it's slow.
                searchBNFs: ModelHelper.getCachedModel('parsedSearchBNFs', {
                    app: this.model.application.get('app'),
                    owner: this.model.application.get('owner'),
                    count: 0,
                }),
            },
        );
        this.model.content.on('change:search', this.handleSearchChange, this);
    }

    componentDidMount() {
        super.componentDidMount();

        // need to wait and render again if searchBNFs is not ready (lazy loaded),
        // otherwise the syntax highlighting will not work.
        if (this.collection.searchBNFs.dfd.state() === 'pending') {
            this.collection.searchBNFs.dfd.done(this.backboneView.render);
        }
    }

    handleSearchChange(model, value) {
        this.props.onChange(null, { value });
    }
    getContainerProps() {
        return Object.assign(createTestHook(module.id), this.props);
    }
    getView() {
        const userPrefSearchAssistant = this.model.user.getSearchAssistant();
        // need to change FULL to COMPACT otherwise it is too wide.
        const searchAssistant = (userPrefSearchAssistant === UserModel.SEARCH_ASSISTANT.FULL) ?
            UserModel.SEARCH_ASSISTANT.COMPACT : userPrefSearchAssistant;
        return new SearchControl({
            showLabel: false,
            showRunSearch: false,
            searchAssistant,
            model: {
                content: this.model.content,
                user: this.model.user,
                application: this.model.application,
            },
            collection: {
                searchBNFs: this.collection.searchBNFs,
            },
            syntaxHighlighting: getSearchEditorTheme(),
        });
    }
}

SearchEditor.propTypes = {
    value: PropTypes.string,
    onChange: PropTypes.func.isRequired,
};

SearchEditor.contextTypes = {
    model: PropTypes.object.isRequired,
    collection: PropTypes.object.isRequired,
};

export default SearchEditor;
