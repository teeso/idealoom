// @flow

import React from 'react';
import ReactDOM from 'react-dom';
import { I18n } from 'react-redux-i18n';

type LeftSideHarvestingButtonProps = {
  label: string,
  handleClick: Function,
  children: Array<*>
};

const LeftSideHarvestingButton = ({ label, handleClick, children }: LeftSideHarvestingButtonProps) => (
  <div className="left-side-harvesting-button">
    <div className="left-side-harvesting-button__label">{label}</div>
    <div className="left-side-harvesting-button__button" role="button" tabIndex={0} onClick={handleClick}>
      <div className="left-side-harvesting-button__button__inside">{children}</div>
    </div>
  </div>
);

type ConfirmHarvestButtonProps = {
  handleClick: Function
};

const ConfirmHarvestButton = ({ handleClick }: ConfirmHarvestButtonProps) => (
  <LeftSideHarvestingButton handleClick={handleClick} label={I18n.t('harvesting.harvestSelection')}>
    <span className="confirm-harvest-button assembl-icon-catch">&nbsp;</span>
  </LeftSideHarvestingButton>
);

type HarvestingMenuProps = {
  positionX: number,
  positionY: number
};

const HarvestingMenu = ({ positionX, positionY }: HarvestingMenuProps) => {
  const style = {
    position: 'absolute',
    left: `${positionX}px`,
    top: `${positionY}px`
  };
  const handleClick = () => {
    // TODO in next story
  };
  return (
    <div className="harvesting-menu" style={style}>
      <ConfirmHarvestButton handleClick={handleClick} />
    </div>
  );
};

const harvestingMenuContainerUniqueId = 'harvesting-menu-container';

export const removeHarvestingMenu = () => {
  const harvestingMenuContainer = document.getElementById(harvestingMenuContainerUniqueId);
  if (harvestingMenuContainer && harvestingMenuContainer.parentNode) {
    harvestingMenuContainer.parentNode.removeChild(harvestingMenuContainer);
  }
};

export const handleMouseUpWhileHarvesting = (evt: SyntheticMouseEvent) => {
  const selObj = window.getSelection();
  const selectedText = selObj.toString();
  if (!selectedText || selectedText.length === 0) {
    removeHarvestingMenu();
    return;
  }

  let harvestingMenuContainer = document.getElementById(harvestingMenuContainerUniqueId);
  if (!harvestingMenuContainer) {
    harvestingMenuContainer = document.createElement('div');
    harvestingMenuContainer.id = harvestingMenuContainerUniqueId;
    document.getElementsByTagName('body')[0].appendChild(harvestingMenuContainer);
  }

  const iconSize = 44;
  const positionX = (window.innerWidth - 600) / 2 - iconSize - 50;
  const positionY = evt.pageY - iconSize / 2;

  ReactDOM.render(<HarvestingMenu positionX={positionX} positionY={positionY} />, harvestingMenuContainer);
};