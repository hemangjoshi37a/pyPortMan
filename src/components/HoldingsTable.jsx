import { useState } from 'react';
import { formatIndianCurrency, formatNumber } from '../data/mockData';

export default function HoldingsTable({ holdings, onRowClick }) {
  const [sortColumn, setSortColumn] = useState('symbol');
  const [sortDirection, setSortDirection] = useState('asc');
  const [searchTerm, setSearchTerm] = useState('');

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const filtered = holdings.filter(holding =>
    holding.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const aValue = a[sortColumn];
    const bValue = b[sortColumn];

    let comparison = 0;
    if (aValue > bValue) comparison = 1;
    if (aValue < bValue) comparison = -1;

    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const SortHeader = ({ column, children }) => (
    <th onClick={() => handleSort(column)} style={{ cursor: 'pointer' }}>
      {children}
      {sortColumn === column && (
        <span style={{ marginLeft: '5px' }}>{sortDirection === 'asc' ? '↑' : '↓'}</span>
      )}
    </th>
  );

  return (
    <div>
      <div className="table-controls">
        <input
          type="text"
          placeholder="Search stocks..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <SortHeader column="symbol">Stock</SortHeader>
              <th>Qty</th>
              <SortHeader column="avgBuyPrice">Avg Buy Price</SortHeader>
              <th>LTP</th>
              <SortHeader column="currentValue">Current Value</SortHeader>
              <SortHeader column="pnl">P&L</SortHeader>
              <SortHeader column="pnlPercent">P&L %</SortHeader>
            </tr>
          </thead>
          <tbody>
            {sorted.map((holding) => (
              <tr
                key={`${holding.accountId}-${holding.symbol}`}
                onClick={() => onRowClick && onRowClick(holding)}
              >
                <td>
                  <div>
                    <div className="stock-symbol">{holding.symbol}</div>
                    <div className="stock-account">{holding.accountName}</div>
                  </div>
                </td>
                <td>{formatNumber(holding.qty)}</td>
                <td>{formatIndianCurrency(holding.avgBuyPrice)}</td>
                <td>{formatIndianCurrency(holding.ltp)}</td>
                <td>{formatIndianCurrency(holding.currentValue)}</td>
                <td className={holding.pnl >= 0 ? 'positive' : 'negative'}>
                  {formatIndianCurrency(holding.pnl)}
                </td>
                <td className={holding.pnl >= 0 ? 'positive' : 'negative'}>
                  {holding.pnlPercent >= 0 ? '+' : ''}{holding.pnlPercent.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
