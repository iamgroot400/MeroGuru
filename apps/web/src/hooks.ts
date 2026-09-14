import { useEffect, useRef, useState } from "react";

export function useAsync<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
) {
  const loader = useRef(load);
  loader.current = load;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{
    key: string;
    data?: T;
    error?: string;
    loading: boolean;
  }>({ key, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ key, loading: true });
    loader
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ key, data, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({
            key,
            error:
              error instanceof Error ? error.message : "Something went wrong.",
            loading: false,
          });
      });
    return () => controller.abort();
  }, [key, revision]);
  return {
    ...(state.key === key
      ? state
      : { loading: true, data: undefined, error: undefined }),
    reload: () => setRevision((v) => v + 1),
  };
}
