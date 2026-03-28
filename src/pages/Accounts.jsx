import { useState } from 'react';
import AccountCard from '../components/AccountCard';
import { accounts, formatIndianCurrency } from '../data/mockData';

export default function Accounts() {
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);

  const handleAddAccount = () => {
    setShowAddForm(true);
    setSelectedAccount(null);
  };

  const handleEditAccount = (account) => {
    setSelectedAccount(account);
    setShowAddForm(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real app, this would save to backend
    console.log('Account saved:', selectedAccount);
    setShowAddForm(false);
    setSelectedAccount(null);
  };

  const totalCurrentValue = accounts.reduce((sum, acc) => sum + acc.currentValue, 0);
  const totalInvestedValue = accounts.reduce((sum, acc) => sum + acc.totalInvested, 0);
  const totalPNL = accounts.reduce((sum, acc) => sum + acc.overallPL, 0);

  return (
    <div className="accounts-page">
      <div className="page-header">
        <h1>Accounts</h1>
        <button className="btn-primary" onClick={handleAddAccount}>
          + Add Account
        </button>
      </div>

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
            account={account}
            onClick={() => {}}
            onEdit={handleEditAccount}
          />
        ))}
      </div>

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
                }}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit} className="account-form">
              <div className="form-group">
                <label>Account Name</label>
                <input
                  type="text"
                  value={selectedAccount ? selectedAccount.name : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, name: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Broker</label>
                <select
                  value={selectedAccount ? selectedAccount.broker : 'zerodha'}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, broker: e.target.value })}
                  required
                >
                  <option value="zerodha">Zerodha</option>
                  <option value="angel">Angel Broking</option>
                </select>
              </div>

              <div className="form-group">
                <label>User ID / Client ID</label>
                <input
                  type="text"
                  value={selectedAccount ? selectedAccount.id : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, id: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={selectedAccount ? selectedAccount.ac_pass || '' : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, ac_pass: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>PIN / 2FA</label>
                <input
                  type="text"
                  value={selectedAccount ? selectedAccount.ac_pin || '' : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, ac_pin: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>API Key</label>
                <input
                  type="text"
                  value={selectedAccount ? selectedAccount.apiKey || '' : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, apiKey: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>API Secret</label>
                <input
                  type="password"
                  value={selectedAccount ? selectedAccount.apiSecret || '' : ''}
                  onChange={(e) => setSelectedAccount({ ...selectedAccount, apiSecret: e.target.value })}
                />
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowAddForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
