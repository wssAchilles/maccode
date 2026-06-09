import { useCallback, useEffect, useState, type DependencyList } from 'react';

export function useAsyncData<T>(loader: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      setData(result);
      return result;
    } catch (err) {
      const nextError = err instanceof Error ? err : new Error(String(err));
      setError(nextError);
      throw nextError;
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    let ignore = false;
    setLoading(true);
    setError(null);
    loader()
      .then((result) => {
        if (!ignore) setData(result);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof Error ? err : new Error(String(err)));
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, deps);

  return { data, error, loading, refetch };
}
