type AuthTokenProvider = (() => Promise<string | undefined>) | null

let tokenProvider: AuthTokenProvider = null

export function setAuthTokenProvider(provider: AuthTokenProvider): void {
  tokenProvider = provider
}

export async function buildRequestHeaders(initial?: HeadersInit): Promise<Headers> {
  const headers = new Headers(initial)
  if (!headers.has('content-type')) {
    headers.set('content-type', 'application/json')
  }

  if (tokenProvider) {
    try {
      const token = await tokenProvider()
      if (token && token.trim().length > 0) {
        headers.set('authorization', `Bearer ${token}`)
      }
    } catch {
      // Ignore token resolution errors and continue as anonymous request.
    }
  }

  return headers
}
