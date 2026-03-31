import { useState, useEffect, useCallback } from 'react';
import { getPositions, getPositionsByAccount, squareoffPosition, squareoffAll, isMarketOpen } from '../services/api';

/**
 * Custom hook for positions data
 * @param {number|null} accountId - Optional account ID to filter positions
 * @returns {Object} - { data, loading, error, refetch, squareoff, squareoffAll }
 */
export function usePositions(accountId = null) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = accountId
        ? await getPositionsByAccount(accountId)
        : await getPositions();
      setData(result);
    } catch (err) {
      if (err.message === 'TOKEN_EXPIRED') {
        setError('TOKEN_EXPIRED');
      } else {
        setError(err.message);
      }
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  const squareoff = useCallback(async (params) => {
    try {
      if (!accountId) {
        throw new Error('Account ID is required for squareoff');
      }
      const result = await squareoffPosition(accountId, params);
      await fetchData();
      return result;
    } catch (err) {
      throw err;
    }
  }, [accountId, fetchData]);

  const squareoffAllPositions = useCallback(async () => {
    try {
      if (!accountId) {
        throw new Error('Account ID is required for squareoff all');
      }
      const result = await squareoffAll(accountId);
      await fetchData();
      return result;
    } catch (err) {
      throw err;
    }
  }, [accountId, fetchData]);

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
    data,
    loading,
    error,
    refetch: fetchData,
    squareoff,
    squareoffAll: squareoffAllPositions,
  };
}

export default usePositions;
