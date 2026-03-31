import { useState } from 'react';
import OrdersTable from '../components/OrdersTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
import { useOrders } from '../hooks/useOrders';
import { useAccounts } from '../hooks/useAccounts';

export default function Orders() {
  const [activeTab, setActiveTab] = useState('pending');
  const [showNewOrderForm, setShowNewOrderForm] = useState(false);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(null);

  const { data: orders, loading, error, refetch, place, cancel } = useOrders();
  const { data: accounts } = useAccounts();

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

  const pendingOrders = orders.filter(o => o.status === 'OPEN' || o.status === 'PENDING');
  const completedOrders = orders.filter(o => o.status === 'COMPLETE' || o.status === 'REJECTED');

  const handleSubmitOrder = async (e) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);

    try {
      const formData = new FormData(e.target);
      const orderData = {
        tradingsymbol: formData.get('symbol').toUpperCase(),
        exchange: formData.get('exchange'),
        transaction_type: formData.get('side'),
        quantity: parseInt(formData.get('qty')),
        order_type: formData.get('type'),
        product: formData.get('product'),
        price: formData.get('type') === 'LIMIT' ? parseFloat(formData.get('price')) : undefined,
        validity: 'DAY',
        variety: 'regular',
      };

      await place(orderData);
      setShowNewOrderForm(false);
      setFormError('');
    } catch (err) {
      setFormError(err.message || 'Failed to place order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelOrder = async (orderId) => {
    if (!window.confirm(`Cancel order ${orderId}?`)) {
      return;
    }

    try {
      setCancelling(orderId);
      await cancel(orderId);
    } catch (err) {
      alert(err.message || 'Failed to cancel order');
    } finally {
      setCancelling(null);
    }
  };

  // Enrich orders data
  const enrichedOrders = orders.map(order => ({
    ...order,
    id: order.order_id,
    accountId: order.account_id.toString(),
    accountName: accounts.find(a => a.id === order.account_id)?.name || 'Unknown',
    symbol: order.stock,
    qty: order.qty,
    type: order.order_type,
    side: order.transaction_type,
    price: order.price,
    status: order.status,
    timestamp: order.placed_at,
  }));

  return (
    <div className="orders-page">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

      <div className="page-header">
        <h1>Orders</h1>
        <button
          className="btn-primary"
          onClick={() => setShowNewOrderForm(true)}
          disabled={accounts.length === 0}
        >
          + New Order
        </button>
      </div>

      {loading && orders.length === 0 ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="large" text="Loading orders..." />
        </div>
      ) : (
        <>
          <div className="orders-tabs">
            <button
              className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveTab('pending')}
            >
              Pending Orders ({pendingOrders.length})
            </button>
            <button
              className={`tab ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              Order History ({completedOrders.length})
            </button>
          </div>

          <div className="orders-content">
            {activeTab === 'pending' && (
              <div>
                <h3>Pending Orders</h3>
                {pendingOrders.length > 0 ? (
                  <OrdersTable
                    orders={enrichedOrders.filter(o => o.status === 'OPEN' || o.status === 'PENDING')}
                    onCancel={handleCancelOrder}
                    cancelling={cancelling}
                  />
                ) : (
                  <div className="text-gray-500 text-sm py-8">No pending orders</div>
                )}
              </div>
            )}

            {activeTab === 'history' && (
              <div>
                <h3>Order History</h3>
                {completedOrders.length > 0 ? (
                  <OrdersTable orders={enrichedOrders.filter(o => o.status === 'COMPLETE' || o.status === 'REJECTED')} />
                ) : (
                  <div className="text-gray-500 text-sm py-8">No order history</div>
                )}
              </div>
            )}
          </div>

          {orders.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-lg">No orders found</p>
                <p className="text-sm mt-2">
                  {accounts.length === 0
                    ? 'Add an account first to place orders'
                    : 'Click "New Order" to place your first order'}
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {showNewOrderForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Place New Order</h2>
              <button
                className="btn-close"
                onClick={() => {
                  setShowNewOrderForm(false);
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

            <form onSubmit={handleSubmitOrder} className="order-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Stock Symbol</label>
                  <input
                    type="text"
                    name="symbol"
                    placeholder="RELIANCE"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Quantity</label>
                  <input
                    type="number"
                    name="qty"
                    placeholder="10"
                    min="1"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Exchange</label>
                  <select name="exchange" required>
                    <option value="NSE">NSE</option>
                    <option value="BSE">BSE</option>
                    <option value="MCX">MCX</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Order Type</label>
                  <select name="type" required>
                    <option value="MARKET">MARKET</option>
                    <option value="LIMIT">LIMIT</option>
                    <option value="SL">STOP LOSS</option>
                    <option value="SL-M">STOP LOSS MARKET</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Side</label>
                  <select name="side" required>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Product</label>
                  <select name="product" required>
                    <option value="CNC">CNC (Delivery)</option>
                    <option value="MIS">MIS (Intraday)</option>
                    <option value="CO">CO (Cover Order)</option>
                    <option value="BO">BO (Bracket Order)</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Price</label>
                  <input
                    type="number"
                    name="price"
                    placeholder="100.00"
                    step="0.05"
                    disabled={true}
                  />
                  <small className="text-gray-500">Only for LIMIT orders</small>
                </div>

                <div className="form-group">
                  <label>Account</label>
                  <select name="account" required>
                    {accounts.map(account => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowNewOrderForm(false);
                    setFormError('');
                  }}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Placing...' : 'Place Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
