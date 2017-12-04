import React from 'react';
import { connect } from 'react-redux';
import { browserHistory } from 'react-router';
import { Translate, Localize } from 'react-redux-i18n';
import { get } from '../../../utils/routeMap';
import { getPhaseStatus, isSeveralIdentifiers } from '../../../utils/timeline';
import { displayModal } from '../../../utils/utilityManager';

class Phase extends React.Component {
  constructor(props) {
    super(props);
    this.displayPhase = this.displayPhase.bind(this);
  }
  displayPhase() {
    const { identifier, startDate, endDate, title } = this.props;
    const { debateData } = this.props.debate;
    const { locale } = this.props.i18n;
    const params = { slug: debateData.slug, phase: identifier };
    let phaseName = '';
    title.entries.forEach((entry) => {
      if (locale === entry['@language']) {
        phaseName = entry.value.toLowerCase();
      }
    });
    const isSeveralPhases = isSeveralIdentifiers(debateData.timeline);
    const phaseStatus = getPhaseStatus(startDate, endDate);
    if (isSeveralPhases) {
      if (phaseStatus === 'notStarted') {
        const body = (
          <div>
            <Translate value="debate.notStarted" phaseName={phaseName} />
            <Localize value={startDate} dateFormat="date.format" />
          </div>
        );
        displayModal(null, body, true, null, null, true);
      }
      if (phaseStatus === 'inProgress' || phaseStatus === 'completed') {
        browserHistory.push(get('debate', params));
      }
    } else {
      browserHistory.push(get('debate', params));
    }
  }
  render() {
    const { locale } = this.props.i18n;
    const { imgUrl, startDate, title, description, index } = this.props;
    const stepNumber = index + 1;
    return (
      <div className="illustration-box">
        <div className="image-box" style={imgUrl ? { backgroundImage: `url(${imgUrl})` } : null} />
        <div onClick={this.displayPhase} className="content-box">
          <h1 className="light-title-1">{stepNumber}</h1>
          {title && (
            <h3 className="light-title-3">
              {title.entries.map((entry, index2) => {
                return <span key={index2}>{locale === entry['@language'] ? entry.value : ''}</span>;
              })}
            </h3>
          )}
          <h4 className="light-title-4">
            <Localize value={startDate} dateFormat="date.format2" />
          </h4>
          {description && (
            <div className="description-box">
              {description.entries.map((entry, index3) => {
                return <span key={index3}>{locale === entry['@language'] ? entry.value : ''}</span>;
              })}
            </div>
          )}
        </div>
        <div className="color-box">&nbsp;</div>
        <div className="box-hyphen">&nbsp;</div>
        <div className="box-hyphen rotate-hyphen">&nbsp;</div>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  return {
    i18n: state.i18n,
    debate: state.debate
  };
};

export default connect(mapStateToProps)(Phase);