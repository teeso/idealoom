// @flow
import React from 'react';
import { connect } from 'react-redux';
import PageForm from '../components/administration/voteSession/pageForm';
import ModulesSection from '../components/administration/voteSession/modulesSection';
import PropositionSection from '../components/administration/voteSession/propositionSection';
import Navbar from '../components/administration/navbar';

type VoteSessionAdminProps = {
  section: string,
  editLocale: string
};

const VoteSessionAdmin = (props: VoteSessionAdminProps) => {
  const currentStep = parseInt(props.section, 10);
  return (
    <div className="token-vote-admin">
      {props.section === '1' && <PageForm editLocale={props.editLocale} />}
      {props.section === '2' && <ModulesSection />}
      {props.section === '3' && <PropositionSection />}
      {!isNaN(currentStep) && <Navbar currentStep={currentStep} totalSteps={3} phaseIdentifier="voteSession" />}
    </div>
  );
};

const mapStateToProps = state => ({
  editLocale: state.admin.editLocale
});

export default connect(mapStateToProps)(VoteSessionAdmin);