import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../i18n/I18nProvider'
import { useFirebaseAuth } from './useFirebaseAuth'

const {
  mockLoadFirebaseAuthServices,
  mockLoadFirebaseAuthModule,
  mockSignInWithEmailAndPassword,
  mockCreateUserWithEmailAndPassword,
  mockSignInWithPopup,
  mockSignOut,
  mockOnAuthStateChanged,
  mockSetAuthTokenProvider,
} = vi.hoisted(() => ({
  mockLoadFirebaseAuthServices: vi.fn(),
  mockLoadFirebaseAuthModule: vi.fn(),
  mockSignInWithEmailAndPassword: vi.fn(),
  mockCreateUserWithEmailAndPassword: vi.fn(),
  mockSignInWithPopup: vi.fn(),
  mockSignOut: vi.fn(),
  mockOnAuthStateChanged: vi.fn(),
  mockSetAuthTokenProvider: vi.fn(),
}))

vi.mock('firebase/auth', () => ({
  signInWithEmailAndPassword: mockSignInWithEmailAndPassword,
  createUserWithEmailAndPassword: mockCreateUserWithEmailAndPassword,
  signInWithPopup: mockSignInWithPopup,
  signOut: mockSignOut,
  onAuthStateChanged: mockOnAuthStateChanged,
}))

vi.mock('../lib/firebase-services', () => ({
  loadFirebaseAuthServices: mockLoadFirebaseAuthServices,
  loadFirebaseAuthModule: mockLoadFirebaseAuthModule,
}))

vi.mock('../lib/auth-session', () => ({
  setAuthTokenProvider: mockSetAuthTokenProvider,
}))

function Harness() {
  const auth = useFirebaseAuth()

  return (
    <div>
      <p data-testid="auth-status">{auth.status}</p>
      <label>
        email
        <input
          aria-label="email"
          value={auth.email}
          onChange={(event) => auth.setEmail(event.target.value)}
        />
      </label>
      <label>
        password
        <input
          aria-label="password"
          type="password"
          value={auth.password}
          onChange={(event) => auth.setPassword(event.target.value)}
        />
      </label>
      <button type="button" onClick={() => void auth.signInWithEmail()}>
        sign-in
      </button>
      <button type="button" onClick={() => void auth.signUpWithEmail()}>
        sign-up
      </button>
      {auth.error ? <p role="alert">{auth.error}</p> : null}
    </div>
  )
}

describe('useFirebaseAuth', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    vi.stubEnv('VITE_FIREBASE_API_KEY', 'demo-api-key')
    vi.stubEnv('VITE_FIREBASE_PROJECT_ID', 'demo-project')
    window.localStorage.setItem('cerberus.locale', 'zh-CN')

    mockOnAuthStateChanged.mockImplementation((_auth, callback: (user: null) => void) => {
      callback(null)
      return vi.fn()
    })
    mockLoadFirebaseAuthServices.mockResolvedValue({
      auth: {
        currentUser: null,
      },
    })
    mockLoadFirebaseAuthModule.mockResolvedValue({
      signInWithEmailAndPassword: mockSignInWithEmailAndPassword,
      createUserWithEmailAndPassword: mockCreateUserWithEmailAndPassword,
      signInWithPopup: mockSignInWithPopup,
      signOut: mockSignOut,
      onAuthStateChanged: mockOnAuthStateChanged,
      GoogleAuthProvider: class {},
    })
    mockLoadFirebaseAuthServices.mockClear()
    mockLoadFirebaseAuthModule.mockClear()
    mockSignInWithEmailAndPassword.mockReset()
    mockCreateUserWithEmailAndPassword.mockReset()
    mockSignInWithPopup.mockReset()
    mockSignOut.mockReset()
    mockSetAuthTokenProvider.mockReset()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    window.localStorage.clear()
  })

  it('uses email sign-in for the login action', async () => {
    mockSignInWithEmailAndPassword.mockResolvedValue({})

    render(
      <I18nProvider>
        <Harness />
      </I18nProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-status').textContent).toBe('ready')
    })

    await userEvent.type(screen.getByLabelText('email'), 'Existing@Example.com')
    await userEvent.type(screen.getByLabelText('password'), 'topsecret')
    await userEvent.click(screen.getByRole('button', { name: 'sign-in' }))

    await waitFor(() => {
      expect(mockSignInWithEmailAndPassword).toHaveBeenCalledWith(
        expect.anything(),
        'existing@example.com',
        'topsecret',
      )
    })

    expect(mockCreateUserWithEmailAndPassword).not.toHaveBeenCalled()
  })

  it('initializes Firebase auth even when there is no persisted session hint', async () => {
    render(
      <I18nProvider>
        <Harness />
      </I18nProvider>,
    )

    expect(screen.getByTestId('auth-status').textContent).toBe('loading')

    await waitFor(() => {
      expect(mockLoadFirebaseAuthServices).toHaveBeenCalled()
    })
  })

  it('uses email sign-up for the create-account action', async () => {
    mockCreateUserWithEmailAndPassword.mockResolvedValue({})

    render(
      <I18nProvider>
        <Harness />
      </I18nProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-status').textContent).toBe('ready')
    })

    await userEvent.type(screen.getByLabelText('email'), 'new-user@example.com')
    await userEvent.type(screen.getByLabelText('password'), 'topsecret')
    await userEvent.click(screen.getByRole('button', { name: 'sign-up' }))

    await waitFor(() => {
      expect(mockCreateUserWithEmailAndPassword).toHaveBeenCalledWith(
        expect.anything(),
        'new-user@example.com',
        'topsecret',
      )
    })

    expect(mockSignInWithEmailAndPassword).not.toHaveBeenCalled()
  })

  it('shows a human-readable message for invalid credentials', async () => {
    mockSignInWithEmailAndPassword.mockRejectedValue({ code: 'auth/invalid-credential' })

    render(
      <I18nProvider>
        <Harness />
      </I18nProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-status').textContent).toBe('ready')
    })

    await userEvent.type(screen.getByLabelText('email'), 'existing@example.com')
    await userEvent.type(screen.getByLabelText('password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'sign-in' }))

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('邮箱或密码不正确')
    })
  })
})
