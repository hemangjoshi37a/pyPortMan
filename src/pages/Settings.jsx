import { useState } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
import { useAccounts } from '../hooks/useAccounts';
import { getAuthLoginUrl, handleAuthCallback } from '../services/api';

export default function Settings() {
  const [activeTab, setActiveTab] = useState('accounts');
  const [editingAccount, setEditingAccount] = useState(null);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);
  const [refreshingToken, setRefreshingToken] = useState(null);
  const [requestToken, setRequestToken] = useState('');
  const [tokenStep, setTokenStep] = useState('idle'); // idle, login, callback, success
  const [loginUrl, setLoginUrl] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: accounts, loading, error, refetch, update, remove, getLoginUrl } = useAccounts();

  // Handle token expired error
  if (error === 'TOKEN_EXPIRED' && accounts.length > 0) {
    setTokenAccountId(accounts[0].id);
    setShowTokenModal(true);
  }

  const handleTokenModalClose = () => {
    setShowTokenModal(false);
    setTokenAccountId(null);
    setTokenStep('idle');
    setLoginUrl('');
    setRequestToken('');
    setFormError('');
    refetch();
  };

  const handleEditAccount = (account) => {
    setEditingAccount(account);
  };

  const handleSaveAccount = async (e) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);

    try {
      const formData = new FormData(e.target);
      const accountData = {
        name: formData.get('name'),
        api_key: formData.get('api_key'),
        api_secret: formData.get('api_secret'),
      };

      await update(editingAccount.id, accountData);
      setEditingAccount(null);
      setFormError('');
    } catch (err) {
      setFormError(err.message || 'Failed to save account');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm('Are you sure you want to delete this account?')) {
      return;
    }

    try {
      await remove(accountId);
    } catch (err) {
      alert(err.message || 'Failed to delete account');
    }
  };

  const handleRefreshToken = async (accountId) => {
    try {
      setRefreshingToken(accountId);
      setTokenStep('login');
      setTokenAccountId(accountId);
      const result = await getAuthLoginUrl(accountId);
      setLoginUrl(result.login_url);
      window.open(result.loginUrl, '_blank');
      setTokenStep('callback');
    } catch (err) {
      setFormError(err.message || 'Failed to get login URL');
      setTokenStep('idle');
    } finally {
      setRefreshingToken(null);
    }
  };

  const handleTokenCallback = async (e) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);

    try {
      await handleAuthCallback({
        account_id: tokenAccountId,
        request_token: requestToken,
      });
      setTokenStep('success');
      setRequestToken('');
    } catch (err) {
      setFormError(err.message || 'Failed to verify token');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRefreshAllTokens = () => {
    if (accounts.length === 0) {
      alert('No accounts to refresh');
      return;
    }
    alert('Please refresh tokens individually for each account');
  };

  return (
    <div className="settings-page">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

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

            {loading && accounts.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <LoadingSpinner text="Loading accounts..." />
              </div>
            ) : (
              <>
                <div className="account-list">
                  {accounts.map(account => (
                    <div key={account.id} className="settings-account-item">
                      <div className="account-info">
                        <h3>{account.name}</h3>
                        <span className={`account-status ${account.is_active ? 'active' : 'inactive'}`}>
                          {account.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <p className="account-details">
                          {account.account_id} • Zerodha
                        </p>
                        {account.last_login_at && (
                          <p className="account-details text-sm text-gray-500">
                            Last login: {new Date(account.last_login_at).toLocaleString('en-IN')}
                          </p>
                        )}
                      </div>
                      <div className="account-actions">
                        <button
                          className="btn-secondary"
                          onClick={() => handleEditAccount(account)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn-secondary"
                          onClick={() => handleRefreshToken(account.id)}
                          disabled={refreshingToken === account.id}
                        >
                          {refreshingToken === account.id ? 'Refreshing...' : 'Refresh Token'}
                        </button>
                        <button
                          className="btn-danger"
                          onClick={() => handleDeleteAccount(account.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {accounts.length === 0 && !loading && (
                  <div className="text-gray-500 text-center py-8">
                    No accounts added yet. Go to Accounts page to add your first account.
                  </div>
                )}

                {editingAccount && (
                  <div className="edit-form">
                    <h3>Edit Account: {editingAccount.name}</h3>
                    {formError && (
                      <div className="bg-red-900/30 border border-red-700 text-red-200 px-4 py-2 rounded mb-4">
                        {formError}
                      </div>
                    )}
                    <form onSubmit={handleSaveAccount} className="settings-form">
                      <div className="form-row">
                        <div className="form-group">
                          <label>Account Name</label>
                          <input
                            type="text"
                            name="name"
                            defaultValue={editingAccount.name}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label>Broker</label>
                          <select value="zerodha" disabled>
                            <option value="zerodha">Zerodha</option>
                          </select>
                        </div>
                      </div>

                      <div className="form-group">
                        <label>User ID</label>
                        <input
                          type="text"
                          defaultValue={editingAccount.account_id}
                          readOnly
                        />
                      </div>

                      <div className="form-row">
                        <div className="form-group">
                          <label>API Key</label>
                          <input
                            type="text"
                            name="api_key"
                            defaultValue={editingAccount.api_key}
                          />
                        </div>
                        <div className="form-group">
                          <label>API Secret</label>
                          <input
                            type="password"
                            name="api_secret"
                            defaultValue={editingAccount.api_secret}
                          />
                        </div>
                      </div>

                      <div className="form-actions">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => {
                            setEditingAccount(null);
                            setFormError('');
                          }}
                          disabled={isSubmitting}
                        >
                          Cancel
                        </button>
                        <button type="submit" className="btn-primary" disabled={isSubmitting}>
                          {isSubmitting ? 'Saving...' : 'Save Account'}
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Token Refresh Modal */}
                {tokenStep !== 'idle' && (
                  <div className="modal-overlay">
                    <div className="modal-content">
                      <div className="modal-header">
                        <h2>Refresh Zerodha Token</h2>
                        <button
                          className="btn-close"
                          onClick={() => {
                            setTokenStep('idle');
                            setLoginUrl('');
                            setRequestToken('');
                            setFormError('');
                          }}
                        >
                          ×
                        </button>
                      </div>

                      {formError && (
                        <div className="bg-red-900/30 border border-red-700 text-red-200 px-4 py-2 rounded mb-4">
                          {formError}
                        </div>
                      )}

                      {tokenStep === 'login' && (
                        <div>
                          <p className="text-gray-300 mb-4">
                            Opening Zerodha login in a new tab...
                          </p>
                          <LoadingSpinner text="Waiting for login..." />
                        </div>
                      )}

                      {tokenStep === 'callback' && (
                        <form onSubmit={handleTokenCallback}>
                          <p className="text-gray-300 mb-4">
                            After logging in, paste the request_token from the URL here. It's the value after
                            <code className="bg-gray-800 px-1 py-0.5 rounded mx-1">request_token=</code>
                          </p>
                          <div className="mb-4">
                            <label className="block text-gray-300 text-sm font-medium mb-2">
                              Request Token
                            </label>
                            <input
                              type="text"
                              value={requestToken}
                              onChange={(e) => setRequestToken(e.target.value)}
                              placeholder="Paste request_token here"
                              className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                              required
                            />
                          </div>
                          <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50"
                          >
                            {isSubmitting ? 'Verifying...' : 'Verify Token'}
                          </button>
                        </form>
                      )}

                      {tokenStep === 'success' && (
                        <div>
                          <div className="bg-green-900/30 border border-green-700 text-green-200 px-4 py-3 rounded mb-4">
                            <p className="font-medium">Success!</p>
                            <p className="text-sm">Your token has been refreshed successfully.</p>
                          </div>
                          <button
                            onClick={() => {
                              setTokenStep('idle');
                              setLoginUrl('');
                              setRequestToken('');
                              setFormError('');
                              refetch();
                            }}
                            className="w-full bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded transition-colors"
                          >
                            Close
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
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
                  <li>Click "Refresh Token" button on any account in Account Management tab</li>
                  <li>Login to Zerodha in the new tab that opens</li>
                  <li>After login, you'll be redirected with a request_token</li>
                  <li>Paste the request_token in the modal that appears</li>
                  <li>Your access token will be generated automatically</li>
                </ol>
              </div>

              <div className="instruction-item">
                <h4>Important Notes:</h4>
                <ul>
                  <li>Zerodha access tokens expire daily at 6 AM IST</li>
                  <li>You need to refresh your token every day before trading</li>
                  <li>Keep your API credentials secure and never share them</li>
                </ul>
              </div>

              <button className="btn-primary" onClick={handleRefreshAllTokens}>
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
