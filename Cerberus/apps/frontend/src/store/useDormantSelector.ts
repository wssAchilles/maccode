import { useRef } from 'react'

import { useCerberusStore } from './index'
import type { RootStore } from './slices/shared'

export function useDormantSelector<T>(
  active: boolean,
  selector: (state: RootStore) => T,
): T {
  const frozenValueRef = useRef<T>(selector(useCerberusStore.getState()))
  const selected = useCerberusStore(active ? selector : () => frozenValueRef.current)

  if (active) {
    frozenValueRef.current = selected
    return selected
  }

  return frozenValueRef.current
}
