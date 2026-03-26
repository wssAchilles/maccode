import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../i18n/I18nProvider'
import { useFirebaseAuth } from './useFirebaseAuth'

const {
  mockSignInWithEmailAndPassword,
  mockCreateUserWithEmailAndPassword,
  mockSignInWithPopup,
  mockSignOut,
  mockOnAuthStateChanged,
  mockSetAuthTokenProvider,
} = vi.hoisted(() => ({
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
  getFirebaseServices: () => ({
    auth: {
      currentUser: null,
    },
  }),
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
        submit
      </button>
      {auth.error ? <p role="alert">{auth.error}</p> : null}
    </div>
  )
}

describe('useFirebaseAuth', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    window.localStorage.setItem('cerberus.locale', 'zh-CN')

    mockOnAuthStateChanged.mockImplementation((_auth, callback: (user: null) => void) => {
      callback(null)
      return vi.fn()
    })
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

  it('uses email sign-in and never attempts implicit registration', async () => {
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
    await userEvent.click(screen.getByRole('button', { name: 'submit' }))

    await waitFor(() => {
      expect(mockSignInWithEmailAndPassword).toHaveBeenCalledWith(
        expect.anything(),
        'existing@example.com',
        'topsecret',
      )
    })

    expect(mockCreateUserWithEmailAndPassword).not.toHaveBeenCalled()
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
    await userEvent.click(screen.getByRole('button', { name: 'submit' }))

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('邮箱或密码不正确')
    })
  })
})
