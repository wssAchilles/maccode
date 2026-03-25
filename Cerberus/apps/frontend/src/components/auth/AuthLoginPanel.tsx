import type { TranslationKey } from '../../i18n/messages'
import type { FirebaseAuthState } from '../../auth/useFirebaseAuth'

type Translate = (key: TranslationKey) => string

type Props = {
  t: Translate
  auth: Pick<
    FirebaseAuthState,
    | 'status'
    | 'error'
    | 'signingIn'
    | 'email'
    | 'password'
    | 'setEmail'
    | 'setPassword'
    | 'signInWithEmailAutoRegister'
    | 'signInWithGoogle'
  >
}

export function AuthLoginPanel({ t, auth }: Props) {
  if (auth.status === 'loading') {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center justify-center p-6 text-white">
        <section className="panel-card w-full">
          <h1 className="text-xl font-bold text-cyan-300">{t('auth.loading')}</h1>
          <p className="mt-2 text-sm text-slate-300">{t('auth.loadingHint')}</p>
        </section>
      </main>
    )
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center justify-center p-6 text-white">
      <section className="panel-card w-full" data-testid="auth-login-panel">
        <h1 className="text-xl font-bold text-cyan-300">{t('auth.title')}</h1>
        <p className="mt-2 text-sm text-slate-300">{t('auth.subtitle')}</p>

        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            void auth.signInWithEmailAutoRegister()
          }}
        >
          <label className="field-label">
            {t('auth.email')}
            <input
              id="auth-email"
              name="email"
              data-testid="auth-email-input"
              className="field-input"
              autoComplete="email"
              inputMode="email"
              type="email"
              value={auth.email}
              onChange={(event) => auth.setEmail(event.target.value)}
              required
            />
          </label>
          <label className="field-label">
            {t('auth.password')}
            <input
              id="auth-password"
              name="password"
              data-testid="auth-password-input"
              className="field-input"
              autoComplete="current-password"
              type="password"
              value={auth.password}
              onChange={(event) => auth.setPassword(event.target.value)}
              required
            />
          </label>

          <button
            type="submit"
            className="action-button action-button-primary w-full"
            disabled={auth.signingIn}
            data-testid="auth-email-submit"
          >
            {auth.signingIn ? t('auth.signingIn') : t('auth.signInEmail')}
          </button>
        </form>

        <button
          type="button"
          className="action-button action-button-secondary mt-3 w-full"
          onClick={() => {
            void auth.signInWithGoogle()
          }}
          disabled={auth.signingIn}
          data-testid="auth-google-submit"
        >
          {t('auth.signInGoogle')}
        </button>

        {auth.error ? (
          <p
            data-testid="auth-error"
            className="mt-3 rounded-lg border border-rose-300/40 bg-rose-400/10 px-3 py-2 text-xs text-rose-100"
          >
            {auth.error}
          </p>
        ) : null}
      </section>
    </main>
  )
}
