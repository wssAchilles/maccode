import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

import { dictionaries, type Locale, type TranslationKey } from './messages'

type MessageVars = Record<string, string | number>

type I18nContextValue = {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey, vars?: MessageVars) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

const STORAGE_KEY = 'cerberus.locale'

function formatMessage(template: string, vars?: MessageVars): string {
  if (!vars) {
    return template
  }

  return Object.entries(vars).reduce((acc, [key, value]) => {
    return acc.replaceAll(`{{${key}}}`, String(value))
  }, template)
}

function resolveInitialLocale(): Locale {
  if (typeof window === 'undefined') {
    return 'zh-CN'
  }

  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (raw === 'zh-CN' || raw === 'en-US') {
    return raw
  }

  const browserLocale = window.navigator.language.toLowerCase()
  return browserLocale.startsWith('zh') ? 'zh-CN' : 'en-US'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => resolveInitialLocale())

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale: (nextLocale) => {
        setLocaleState(nextLocale)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(STORAGE_KEY, nextLocale)
        }
      },
      t: (key, vars) => {
        const template = dictionaries[locale][key] ?? key
        return formatMessage(template, vars)
      },
    }),
    [locale],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useI18n must be used inside I18nProvider')
  }
  return context
}
