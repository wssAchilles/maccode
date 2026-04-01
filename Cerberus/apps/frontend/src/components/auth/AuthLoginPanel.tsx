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
  const loading = auth.status === 'loading'
  const formDisabled = loading || auth.signingIn
  const statusMessage = auth.signingIn ? t('auth.signingIn') : undefined

  return (
    <main className="auth-shell" aria-busy={loading}>
      <GlassPanel className="auth-panel" tone="hero" data-testid="auth-login-panel">
        <p className="wb-eyebrow">{t('app.kicker')}</p>
        <h1 className="auth-title">{t('app.title')}</h1>
        <p className="auth-subtitle">{t('app.subtitle')}</p>
        <p className="subtle-label auth-intent">{t('auth.title')}</p>
        <p className="panel-caption">{t('auth.subtitle')}</p>
        <p className="auth-statusline" role="status" aria-live="polite">
          {statusMessage ?? '\u00A0'}
        </p>

        {auth.error ? (
          <InlineAlert title={t('common.error')} tone="danger" className="auth-error" data-testid="auth-error">
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
              disabled={formDisabled}
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
              disabled={formDisabled}
              onChange={(event) => auth.setPassword(event.target.value)}
              required
            />
          </label>

          <div className="auth-actions">
            <button
              type="submit"
              className="soft-button sbp auth-submit"
              disabled={formDisabled}
              data-testid="auth-email-submit"
            >
              {t('auth.signInEmail')}
            </button>
            <button
              type="button"
              className="soft-button auth-submit"
              disabled={formDisabled}
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
          disabled={formDisabled}
          data-testid="auth-google-submit"
        >
          {t('auth.signInGoogle')}
        </button>
      </GlassPanel>
    </main>
  )
}
