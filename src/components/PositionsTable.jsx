import { formatIndianCurrency, formatNumber } from '../services/api';

export default function PositionsTable({ positions, onSquareOff, squaringOff }) {
  const getProductBadgeClass = (product) => {
    switch (product.toUpperCase()) {
      case 'MIS':
        return 'product-mis';
      case 'CNC':
        return 'product-cnc';
      case 'NRML':
        return 'product-nrml';
      default:
        return 'product-default';
    }
  };

  return (
    <div>
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Stock</th>
              <th>Product</th>
              <th>Qty</th>
              <th>Avg Price</th>
              <th>LTP</th>
              <th>P&L</th>
              <th>Day Change</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id}>
                <td>{position.accountName}</td>
                <td>{position.symbol}</td>
                <td>
                  <span className={`badge ${getProductBadgeClass(position.product)}`}>
                    {position.product}
                  </span>
                </td>
                <td>{formatNumber(position.qty)}</td>
                <td>{formatIndianCurrency(position.avgPrice)}</td>
                <td>{formatIndianCurrency(position.ltp)}</td>
                <td className={position.pnl >= 0 ? 'positive' : 'negative'}>
                  {formatIndianCurrency(position.pnl)}
                </td>
                <td className={position.dayChange >= 0 ? 'positive' : 'negative'}>
                  {position.dayChange >= 0 ? '+' : ''}{position.dayChange.toFixed(2)}%
                </td>
                <td>
                  <button
                    className="btn-square-off"
                    onClick={() => onSquareOff && onSquareOff(position)}
                    disabled={squaringOff === position.id}
                  >
                    {squaringOff === position.id ? 'Squaring Off...' : 'Square Off'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
