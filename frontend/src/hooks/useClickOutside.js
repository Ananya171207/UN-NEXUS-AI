import { useEffect } from 'react';

// Calls `handler` when the user clicks outside the element held by `ref`.
// Used to close dropdowns and pop-overs.
export default function useClickOutside(ref, handler) {
  useEffect(() => {
    function onPointerDown(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        handler();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [ref, handler]);
}
