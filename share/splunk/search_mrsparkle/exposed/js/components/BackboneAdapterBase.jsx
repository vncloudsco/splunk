import React, { Component } from 'react';

class BackboneAdapterBase extends Component {

    componentDidMount() {
        this.backboneView = this.getView();
        this.backboneView.render().$el.appendTo(this.container);
    }

    shouldComponentUpdate() {
        return false;
    }

    componentWillUnmount() {
        if (this.backboneView) {
            this.backboneView.remove();
        }
    }

    getView() { // eslint-disable-line class-methods-use-this
        throw new Error('getView() not implemented');
    }

    getContainerProps() {
        // subclass can override this method to return a subset of props.
        // by default it will just pass through all props.
        return this.props;
    }

    render() {
        return (
            <div
                {...this.getContainerProps()}
                ref={(c) => { this.container = c; }}
            />
        );
    }
}

export default BackboneAdapterBase;
