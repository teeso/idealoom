import React from 'react';
import { connect } from 'react-redux';
import { compose, graphql } from 'react-apollo';
import Header from '../components/debate/survey/header';
import withLoadingIndicator from '../components/common/withLoadingIndicator';
import Post from '../components/debate/thread/post';
import IdeaWithPosts from '../graphql/IdeaWithPosts.graphql';

class Idea extends React.Component {
  render() {
    const { idea } = this.props.data;
    return (
      <section className="survey">
        <div className="relative">
          <Header title={idea.title} imgUrl={idea.imgUrl} />
          <div>
            {idea.posts.edges.map((edge) => {
              return <Post {...edge.node} key={edge.node.id} />;
            })}
          </div>
        </div>
      </section>
    );
  }
}

const mapStateToProps = (state) => {
  return {
    lang: state.i18n.locale
  };
};

export default compose(connect(mapStateToProps), graphql(IdeaWithPosts), withLoadingIndicator())(Idea);