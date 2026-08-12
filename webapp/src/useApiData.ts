import { useEffect, useState } from "react";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ok"; data: T };

/** Общий загрузчик для всех 4 страниц — избегаем повторения одного и того
 * же loading/error/ok стейта в каждой странице по отдельности. */
export function useApiData<T>(fetcher: () => Promise<T>): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "ok", data });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: err instanceof Error ? err.message : "Неизвестная ошибка",
          });
        }
      });

    return () => {
      cancelled = true;
    };
    // fetcher передаётся как стабильная ссылка (см. вызовы в pages/*)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return state;
}
