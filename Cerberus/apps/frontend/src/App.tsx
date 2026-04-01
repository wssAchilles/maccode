import { lazy, Suspense } from 'react'

import { AuthGate } from './features/auth/AuthGate'
import { useI18n } from './i18n/I18nProvider'

const LazyAuthenticatedAppShell = lazy(() =>
  import('./features/shell/AuthenticatedAppShell').then((module) => ({
    default: module.AuthenticatedAppShell,
  })),
)

export default function App() {
  const { t } = useI18n()

  return (
    <AuthGate>
      {(auth) => (
        <Suspense fallback={<main className="app-shell"><div className="ws-loading">{t('workspace.loading')}</div></main>}>
          <LazyAuthenticatedAppShell auth={auth} />
        </Suspense>
      )}
    </AuthGate>
  )
}
