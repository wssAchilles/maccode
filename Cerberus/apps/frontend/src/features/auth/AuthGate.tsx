import type { ReactNode } from 'react'

import { useFirebaseAuth, type FirebaseAuthState } from '../../auth/useFirebaseAuth'
import { AuthLoginPanel } from '../../components/auth/AuthLoginPanel'
import { useI18n } from '../../i18n/I18nProvider'

type Props = {
  children: (auth: FirebaseAuthState) => ReactNode
}

export function AuthGate({ children }: Props) {
  const { t } = useI18n()
  const auth = useFirebaseAuth()

  if (auth.required && (auth.status === 'loading' || !auth.user)) {
    return <AuthLoginPanel t={t} auth={auth} />
  }

  return <>{children(auth)}</>
}
