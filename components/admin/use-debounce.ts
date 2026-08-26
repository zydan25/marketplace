import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useDebouncedValue – Returns a debounced version of the input.
 * Waits `delay` ms after the last change before updating.
 */
export function useDebouncedValue<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

/**
 * useDebouncedCallback – Returns a stable callback that fires at most once per `delay` ms.
 */
export function useDebouncedCallback<T extends (...args: never[]) => void>(callback: T, delay = 350) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => callback(...args), delay);
    },
    [callback, delay],
  );
}
