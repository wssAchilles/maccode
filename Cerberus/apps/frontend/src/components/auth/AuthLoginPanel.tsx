import type { TranslationKey } from '../../i18n/messages'
import type { FirebaseAuthState } from '../../auth/useFirebaseAuth'
import { GlassPanel, InlineAlert } from '../../ui'

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
    | 'signInWithEmail'
    | 'signUpWithEmail'
    | 'signInWithGoogle'
  >
}

export function AuthLoginPanel({ t, auth }: Props) {
  if (auth.status === 'loading') {
    return (
      <main className="auth-shell">
        <GlassPanel className="auth-panel" tone="hero">
          <p className="workbench-eyebrow">{t('app.kicker')}</p>
          <h1 className="auth-title">{t('auth.loading')}</h1>
          <p className="auth-subtitle">{t('auth.loadingHint')}</p>
        </GlassPanel>
      </main>
    )
  }

  return (
    <main className="auth-shell">
      <GlassPanel className="auth-panel" tone="hero" data-testid="auth-login-panel">
        <p className="workbench-eyebrow">{t('app.kicker')}</p>
        <h1 className="auth-title">{t('auth.title')}</h1>
        <p className="auth-subtitle">{t('auth.subtitle')}</p>

        {auth.error ? (
          <InlineAlert title={t('common.error')} tone="danger" className="auth-error">
            {auth.error}
          </InlineAlert>
        ) : null}

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault()
            void auth.signInWithEmail()
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

          <div className="auth-actions">
            <button
              type="submit"
              className="soft-button soft-button-primary auth-submit"
              disabled={auth.signingIn}
              data-testid="auth-email-submit"
            >
              {auth.signingIn ? t('auth.signingIn') : t('auth.signInEmail')}
            </button>
            <button
              type="button"
              className="soft-button auth-submit"
              disabled={auth.signingIn}
              data-testid="auth-email-signup"
              onClick={() => {
                void auth.signUpWithEmail()
              }}
            >
              {t('auth.createAccountEmail')}
            </button>
          </div>
        </form>

        <button
          type="button"
          className="soft-button auth-google"
          onClick={() => {
            void auth.signInWithGoogle()
          }}
          disabled={auth.signingIn}
          data-testid="auth-google-submit"
        >
          {t('auth.signInGoogle')}
        </button>
      </GlassPanel>
    </main>
  )
}
