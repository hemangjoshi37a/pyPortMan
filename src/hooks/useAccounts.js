import { useState, useEffect, useCallback } from 'react';
import { getAccounts, addAccount, updateAccount, deleteAccount, getLoginUrl, isMarketOpen } from '../services/api';

/**
 * Custom hook for accounts data
 * @returns {Object} - { data, loading, error, refetch, add, update, remove, getLoginUrl }
 */
export function useAccounts() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getAccounts();
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
  }, []);

  const add = useCallback(async (accountData) => {
    try {
      const result = await addAccount(accountData);
      await fetchData();
      return result;
    } catch (err) {
      throw err;
    }
  }, [fetchData]);

  const update = useCallback(async (id, accountData) => {
    try {
      const result = await updateAccount(id, accountData);
      await fetchData();
      return result;
    } catch (err) {
      throw err;
    }
  }, [fetchData]);

  const remove = useCallback(async (id) => {
    try {
      await deleteAccount(id);
      await fetchData();
    } catch (err) {
      throw err;
    }
  }, [fetchData]);

  const getLoginUrlForAccount = useCallback(async (accountId) => {
    try {
      const result = await getLoginUrl(accountId);
      return result.login_url;
    } catch (err) {
      throw err;
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
    data,
    loading,
    error,
    refetch: fetchData,
    add,
    update,
    remove,
    getLoginUrl: getLoginUrlForAccount,
  };
}

export default useAccounts;
