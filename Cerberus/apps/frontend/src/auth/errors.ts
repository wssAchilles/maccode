import type { Locale } from '../i18n/messages'

type AuthMessageKey =
  | 'missingCredentials'
  | 'missingConfig'
  | 'invalidCredentials'
  | 'emailInUse'
  | 'weakPassword'
  | 'popupCancelled'
  | 'popupBlocked'
  | 'networkFailed'
  | 'tooManyRequests'
  | 'operationNotAllowed'
  | 'invalidEmail'
  | 'unauthorizedDomain'
  | 'generic'

const AUTH_MESSAGES: Record<Locale, Record<AuthMessageKey, string>> = {
  'zh-CN': {
    missingCredentials: '请输入邮箱和密码。',
    missingConfig: '登录服务尚未完成配置，请联系管理员。',
    invalidCredentials: '邮箱或密码不正确，请重新输入。',
    emailInUse: '该邮箱已注册，请直接登录。',
    weakPassword: '密码至少需要 6 位，请重新设置。',
    popupCancelled: '你已取消 Google 登录。',
    popupBlocked: '浏览器拦截了登录弹窗，请允许弹窗后重试。',
    networkFailed: '网络异常，请检查连接后重试。',
    tooManyRequests: '尝试次数过多，请稍后再试。',
    operationNotAllowed: '当前环境未启用该登录方式。',
    invalidEmail: '请输入有效的邮箱地址。',
    unauthorizedDomain: '当前域名未加入 Firebase 授权列表。',
    generic: '登录失败，请稍后重试。',
  },
  'en-US': {
    missingCredentials: 'Enter both email and password.',
    missingConfig: 'Authentication is not configured for this environment.',
    invalidCredentials: 'Incorrect email or password. Try again.',
    emailInUse: 'This email is already registered. Sign in instead.',
    weakPassword: 'Use a password with at least 6 characters.',
    popupCancelled: 'Google sign-in was canceled.',
    popupBlocked: 'The browser blocked the sign-in popup. Allow popups and try again.',
    networkFailed: 'Network error. Check your connection and try again.',
    tooManyRequests: 'Too many attempts. Try again later.',
    operationNotAllowed: 'This sign-in method is not enabled for the current environment.',
    invalidEmail: 'Enter a valid email address.',
    unauthorizedDomain: 'This domain is not authorized for Firebase Authentication.',
    generic: 'Sign-in failed. Please try again later.',
  },
}

export function getAuthMessage(locale: Locale, key: AuthMessageKey): string {
  return AUTH_MESSAGES[locale][key]
}

export function describeAuthError(error: unknown, locale: Locale): string {
  const code = (error as { code?: unknown }).code
  const message = (error as { message?: unknown }).message

  if (typeof code === 'string' && code.length > 0) {
    switch (code) {
      case 'auth/invalid-credential':
      case 'auth/invalid-login-credentials':
      case 'auth/wrong-password':
      case 'auth/user-not-found':
        return getAuthMessage(locale, 'invalidCredentials')
      case 'auth/email-already-in-use':
        return getAuthMessage(locale, 'emailInUse')
      case 'auth/weak-password':
        return getAuthMessage(locale, 'weakPassword')
      case 'auth/popup-closed-by-user':
        return getAuthMessage(locale, 'popupCancelled')
      case 'auth/popup-blocked':
        return getAuthMessage(locale, 'popupBlocked')
      case 'auth/network-request-failed':
        return getAuthMessage(locale, 'networkFailed')
      case 'auth/too-many-requests':
        return getAuthMessage(locale, 'tooManyRequests')
      case 'auth/operation-not-allowed':
        return getAuthMessage(locale, 'operationNotAllowed')
      case 'auth/invalid-email':
        return getAuthMessage(locale, 'invalidEmail')
      case 'auth/unauthorized-domain':
        return getAuthMessage(locale, 'unauthorizedDomain')
      default:
        break
    }
  }

  if (typeof message === 'string' && message.length > 0) {
    return message
  }

  return getAuthMessage(locale, 'generic')
}
