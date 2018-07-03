// @flow
import React from 'react';
import { Translate } from 'react-redux-i18n';
import classnames from 'classnames';
import CookieToggle from './cookieToggle';

const TRANSLATION_KEYS = ['essential', 'analytics'];

type CookiesSelectorProps = {

};

type CookiesSelectorState = {
  activeKey: ?string,
  show: boolean
}

const mockCookiesList = ['premier cookie', '2eme cookie sympa', 'encore un autre'];

class CookiesSelector extends React.Component<CookiesSelectorProps, CookiesSelectorState> {
  constructor(props: CookiesSelectorProps) {
    super(props);
    this.state = {
      activeKey: null,
      show: false
    };
  }


  render() {
    const { activeKey, show } = this.state;
    return (
      <div className="cookies-selector page-body">
        {TRANSLATION_KEYS.map((key) => {
          const isActiveKey = key === activeKey;
          const isEssential = key === 'essential';
          return (
            <div key={`category-${key}`}>
              <div
                className="cookies-category-selector"
                onClick={() => {
                  this.setState({ activeKey: key, show: !show });
                  return key !== activeKey && this.setState({ show: true });
                }}
              >
                <span className={classnames('assembl-icon-right-dir', { 'active-arrow': isActiveKey })} />
                <Translate value={`cookiesPolicy.${key}`} className="dark-title-4" />
              </div>
              <div className="cookies-toggles">
                {isActiveKey && show &&
                mockCookiesList.map(cookie => (
                  <CookieToggle name={cookie} isEssential={isEssential} key={cookie} />
                ))
                }
              </div>
            </div>
          );
        })}
      </div>);
  }
}

export default CookiesSelector;