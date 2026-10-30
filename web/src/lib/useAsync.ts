import { useEffect, useState } from "react";

export type AsyncState<T> = { data?: T; error?: string };

export function useAsync<T>(fn: () => Promise<T>): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({});
  useEffect(() => {
    let alive = true;
    fn().then(
      (data) => alive && setState({ data }),
      (e: unknown) => alive && setState({ error: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return state;
}
