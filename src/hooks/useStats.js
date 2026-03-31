import { useState, useEffect, useCallback } from 'react';
import {
  getSummary,
  getEquityData,
  getAllocation,
  getTopGainers,
  getTopLosers,
  isMarketOpen,
} from '../services/api';

/**
 * Custom hook for portfolio stats
 * @returns {Object} - { summary, equityData, allocation, topGainers, topLosers, loading, error, refetch }
 */
export function useStats() {
  const [summary, setSummary] = useState({
    total_value: 0,
    investment_value: 0,
    day_pnl: 0,
    day_pnl_percent: 0,
    holdings_count: 0,
    positions_count: 0,
    accounts_count: 0,
  });
  const [equityData, setEquityData] = useState([]);
  const [allocation, setAllocation] = useState([]);
  const [topGainers, setTopGainers] = useState([]);
  const [topLosers, setTopLosers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryResult, equityResult, allocationResult, gainersResult, losersResult] =
        await Promise.all([
          getSummary(),
          getEquityData(30),
          getAllocation(),
          getTopGainers(5),
          getTopLosers(5),
        ]);

      setSummary(summaryResult);
      setEquityData(equityResult);
      setAllocation(allocationResult);
      setTopGainers(gainersResult);
      setTopLosers(losersResult);
    } catch (err) {
      if (err.message === 'TOKEN_EXPIRED') {
        setError('TOKEN_EXPIRED');
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    // Auto-refresh every 60 seconds during market hours
    let interval;
    if (isMarketOpen()) {
      interval = setInterval(fetchData, 60000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchData]);

  return {
    summary,
    equityData,
    allocation,
    topGainers,
    topLosers,
    loading,
    error,
    refetch: fetchData,
  };
}

export default useStats;
