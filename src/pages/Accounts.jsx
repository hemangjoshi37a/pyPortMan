import { useState } from 'react';
import AccountCard from '../components/AccountCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
import { useAccounts } from '../hooks/useAccounts';
import { formatIndianCurrency } from '../services/api';

export default function Accounts() {
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: accounts, loading, error, refetch, add, update, remove, getLoginUrl } = useAccounts();

  const handleAddAccount = () => {
    setShowAddForm(true);
    setSelectedAccount(null);
    setFormError('');
  };

  const handleEditAccount = (account) => {
    setSelectedAccount(account);
    setShowAddForm(true);
    setFormError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);

    try {
      const formData = new FormData(e.target);
      const accountData = {
        name: formData.get('name'),
        account_id: formData.get('account_id'),
        api_key: formData.get('api_key'),
        api_secret: formData.get('api_secret'),
      };

      if (selectedAccount) {
        await update(selectedAccount.id, accountData);
      } else {
        await add(accountData);
      }

      setShowAddForm(false);
      setSelectedAccount(null);
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
      const loginUrl = await getLoginUrl(accountId);
      window.open(loginUrl, '_blank');
    } catch (err) {
      alert(err.message || 'Failed to get login URL');
    }
  };

  // Handle token expired error
  if (error === 'TOKEN_EXPIRED' && accounts.length > 0) {
    setTokenAccountId(accounts[0].id);
    setShowTokenModal(true);
  }

  const handleTokenModalClose = () => {
    setShowTokenModal(false);
    setTokenAccountId(null);
    refetch();
  };

  const totalCurrentValue = accounts.reduce((sum, acc) => {
    // Calculate from holdings if available, otherwise use placeholder
    return sum + (acc.current_value || 0);
  }, 0);

  const totalInvestedValue = accounts.reduce((sum, acc) => {
    return sum + (acc.investment_value || 0);
  }, 0);

  const totalPNL = accounts.reduce((sum, acc) => {
    return sum + (acc.day_pnl || 0);
  }, 0);

  return (
    <div className="accounts-page">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

      <div className="page-header">
        <h1>Accounts</h1>
        <button className="btn-primary" onClick={handleAddAccount}>
          + Add Account
        </button>
      </div>

      {loading && accounts.length === 0 ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="large" text="Loading accounts..." />
        </div>
      ) : (
        <>
          <div className="accounts-summary">
            <div className="summary-card">
              <div className="summary-label">Total Invested</div>
              <div className="summary-value">{formatIndianCurrency(totalInvestedValue)}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Current Value</div>
              <div className="summary-value">{formatIndianCurrency(totalCurrentValue)}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Total P&L</div>
              <div className={`summary-value ${totalPNL >= 0 ? 'positive' : 'negative'}`}>
                {formatIndianCurrency(Math.abs(totalPNL))}
              </div>
            </div>
          </div>

          <div className="accounts-grid">
            {accounts.map(account => (
              <AccountCard
                key={account.id}
                account={{
                  ...account,
                  id: account.id.toString(),
                  name: account.name,
                  broker: 'zerodha',
                  status: account.is_active ? 'active' : 'inactive',
                  totalInvested: account.investment_value || 0,
                  currentValue: account.current_value || 0,
                  dayPL: account.day_pnl || 0,
                  overallPL: account.day_pnl || 0,
                }}
                onClick={() => {}}
                onEdit={handleEditAccount}
                onDelete={handleDeleteAccount}
                onRefreshToken={() => handleRefreshToken(account.id)}
              />
            ))}
          </div>

          {accounts.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                </svg>
                <p className="text-lg">No accounts added yet</p>
                <p className="text-sm mt-2">Click "Add Account" to get started</p>
              </div>
            </div>
          )}
        </>
      )}

      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{selectedAccount ? 'Edit Account' : 'Add New Account'}</h2>
              <button
                className="btn-close"
                onClick={() => {
                  setShowAddForm(false);
                  setSelectedAccount(null);
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

            <form onSubmit={handleSubmit} className="account-form">
              <div className="form-group">
                <label>Account Name</label>
                <input
                  type="text"
                  name="name"
                  defaultValue={selectedAccount ? selectedAccount.name : ''}
                  placeholder="e.g., Main Account"
                  required
                />
              </div>

              <div className="form-group">
                <label>Zerodha User ID</label>
                <input
                  type="text"
                  name="account_id"
                  defaultValue={selectedAccount ? selectedAccount.account_id : ''}
                  placeholder="e.g., ABC1234"
                  required
                />
              </div>

              <div className="form-group">
                <label>API Key</label>
                <input
                  type="text"
                  name="api_key"
                  defaultValue={selectedAccount ? selectedAccount.api_key : ''}
                  placeholder="e.g., abc123xyz"
                  required
                />
              </div>

              <div className="form-group">
                <label>API Secret</label>
                <input
                  type="password"
                  name="api_secret"
                  defaultValue={selectedAccount ? selectedAccount.api_secret : ''}
                  placeholder="e.g., secret123"
                  required
                />
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowAddForm(false);
                    setSelectedAccount(null);
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
        </div>
      )}
    </div>
  );
}
