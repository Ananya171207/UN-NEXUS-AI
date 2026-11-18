import { useEffect, useState } from 'react';

// Like useState, but the value is also saved in this browser so it survives
// a page refresh. If the browser blocks storage, it quietly works in memory.
// `initial` should be a constant defined outside the component.
export default function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // storage unavailable (private mode, full, blocked) — ignore
    }
  }, [key, value]);

  return [value, setValue];
}
