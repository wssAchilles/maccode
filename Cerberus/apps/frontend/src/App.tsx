import { useEffect } from 'react'

import { useAppBootstrap } from './app/bootstrap/useAppBootstrap'
import { type FirebaseAuthState } from './auth/useFirebaseAuth'
import { AuthGate } from './features/auth/AuthGate'
import { WorkbenchShell } from './features/shell/WorkbenchShell'
import { useI18n } from './i18n/I18nProvider'
import { formatAppError } from './lib/http'
import { useCerberusStore } from './store'

function AppContent({ auth }: { auth: FirebaseAuthState }) {
  const { locale, setLocale: setI18nLocale } = useI18n()
  const storeLocale = useCerberusStore((state) => state.uiState.locale)
  const summaryError = useCerberusStore((state) => state.strategySummary.last_error)
  const announce = useCerberusStore((state) => state.uiActions.announce)

  const isAuthenticated = !auth.required || Boolean(auth.user)

  useAppBootstrap({ enabled: isAuthenticated })

  useEffect(() => {
    if (storeLocale !== locale) {
      setI18nLocale(storeLocale)
    }
  }, [locale, setI18nLocale, storeLocale])

  useEffect(() => {
    if (!isAuthenticated) {
      return
    }
    void import('./lib/firebase').then((module) => {
      module.initFirebase()
    })
  }, [isAuthenticated])

  useEffect(() => {
    if (summaryError) {
      announce(formatAppError(summaryError))
    }
  }, [announce, summaryError])

  return <WorkbenchShell auth={auth} />
}

export default function App() {
  return <AuthGate>{(auth) => <AppContent auth={auth} />}</AuthGate>
}
