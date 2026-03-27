import { useState } from 'react';
import { accounts } from '../data/mockData';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('accounts');
  const [editingAccount, setEditingAccount] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    broker: 'zerodha',
    id: '',
    ac_pass: '',
    ac_pin: '',
    apiKey: '',
    apiSecret: '',
    totpEnabled: false,
    totpKey: ''
  });

  const handleEditAccount = (account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      broker: account.broker,
      id: account.id,
      ac_pass: account.ac_pass || '',
      ac_pin: account.ac_pin || '',
      apiKey: account.apiKey || '',
      apiSecret: account.apiSecret || '',
      totpEnabled: account.totpEnabled || false,
      totpKey: account.totpKey || ''
    });
  };

  const handleSaveAccount = (e) => {
    e.preventDefault();
    console.log('Saving account:', formData);
    setEditingAccount(null);
  };

  const handleRefreshToken = () => {
    // Simulate token refresh
    alert('Access token refreshed successfully!');
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <div className="settings-tabs">
        <button
          className={`tab ${activeTab === 'accounts' ? 'active' : ''}`}
          onClick={() => setActiveTab('accounts')}
        >
          Account Management
        </button>
        <button
          className={`tab ${activeTab === 'api' ? 'active' : ''}`}
          onClick={() => setActiveTab('api')}
        >
          API Configuration
        </button>
        <button
          className={`tab ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          General Settings
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'accounts' && (
          <div className="settings-section">
            <h2>Account Credentials</h2>

            <div className="account-list">
              {accounts.map(account => (
                <div key={account.id} className="settings-account-item">
                  <div className="account-info">
                    <h3>{account.name}</h3>
                    <span className={`account-status ${account.status}`}>{account.status}</span>
                    <p className="account-details">
                      {account.id} • {account.broker.toUpperCase()}
                    </p>
                  </div>
                  <button
                    className="btn-secondary"
                    onClick={() => handleEditAccount(account)}
                  >
                    Edit
                  </button>
                </div>
              ))}
            </div>

            {editingAccount && (
              <div className="edit-form">
                <h3>Edit Account: {editingAccount.name}</h3>
                <form onSubmit={handleSaveAccount} className="settings-form">
                  <div className="form-row">
                    <div className="form-group">
                      <label>Account Name</label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Broker</label>
                      <select
                        value={formData.broker}
                        onChange={(e) => setFormData({ ...formData, broker: e.target.value })}
                        disabled
                      >
                        <option value="zerodha">Zerodha</option>
                        <option value="angel">Angel Broking</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label>{formData.broker === 'zerodha' ? 'User ID' : 'Client ID'}</label>
                    <input type="text" value={formData.id} readOnly />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Password</label>
                      <input
                        type="password"
                        value={formData.ac_pass}
                        onChange={(e) => setFormData({ ...formData, ac_pass: e.target.value })}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>PIN / 2FA</label>
                      <input
                        type="text"
                        value={formData.ac_pin}
                        onChange={(e) => setFormData({ ...formData, ac_pin: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>API Key</label>
                      <input
                        type="text"
                        value={formData.apiKey}
                        onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label>API Secret</label>
                      <input
                        type="password"
                        value={formData.apiSecret}
                        onChange={(e) => setFormData({ ...formData, apiSecret: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.totpEnabled}
                          onChange={(e) => setFormData({ ...formData, totpEnabled: e.target.checked })}
                        />
                        Enable TOTP
                      </label>
                    </div>
                    {formData.totpEnabled && (
                      <div className="form-group">
                        <label>TOTP Key</label>
                        <input
                          type="text"
                          value={formData.totpKey}
                          onChange={(e) => setFormData({ ...formData, totpKey: e.target.value })}
                        />
                      </div>
                    )}
                  </div>

                  <div className="form-actions">
                    <button type="button" className="btn-secondary" onClick={() => setEditingAccount(null)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary">
                      Save Account
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {activeTab === 'api' && (
          <div className="settings-section">
            <h2>API Configuration</h2>

            <div className="api-instructions">
              <h3>How to Refresh Access Tokens</h3>

              <div className="instruction-item">
                <h4>For Zerodha:</h4>
                <ol>
                  <li>Login to <a href="https://kite.zerodha.com" target="_blank" rel="noopener noreferrer">kite.zerodha.com</a></li>
                  <li>Go to "API" section in your profile</li>
                  <li>Generate new access token</li>
                  <li>Copy and paste below</li>
                </ol>
              </div>

              <div className="instruction-item">
                <h4>For Angel Broking:</h4>
                <ol>
                  <li>Login to <a href="https://smartapi.angelbroking.com" target="_blank" rel="noopener noreferrer">Angel Broking Developer Portal</a></li>
                  <li>Generate JWT token</li>
                  <li>Copy and paste below</li>
                </ol>
              </div>

              <button className="btn-primary" onClick={handleRefreshToken}>
                Refresh All Tokens
              </button>
            </div>
          </div>
        )}

        {activeTab === 'general' && (
          <div className="settings-section">
            <h2>General Settings</h2>

            <div className="settings-form">
              <div className="form-group">
                <label>Dashboard Refresh Interval (seconds)</label>
                <select>
                  <option value="5">5 seconds</option>
                  <option value="10" selected>10 seconds</option>
                  <option value="30">30 seconds</option>
                  <option value="60">1 minute</option>
                </select>
              </div>

              <div className="form-group">
                <label>Date Format</label>
                <select>
                  <option value="en-IN" selected>DD MMM YYYY (Indian)</option>
                  <option value="en-US">MMM DD, YYYY (US)</option>
                  <option value="iso">YYYY-MM-DD (ISO)</option>
                </select>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" defaultChecked />
                  Enable notifications for order status
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" defaultChecked />
                  Show day change on holdings
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" />
                  Dark mode (already enabled)
                </label>
              </div>

              <div className="form-actions">
                <button className="btn-primary">Save Settings</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
