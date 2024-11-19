const SERVER_URL = process.env.SERVER_URL || 'http://localhost:8000'

export function getServerRequest(path: string): Promise<Response> {
  return fetch(`${SERVER_URL}/${path}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

export function postServerRequest(
  path: string,
  body: Record<string, unknown>
): Promise<Response> {
  return fetch(`${SERVER_URL}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

export function loginRequest(formData: URLSearchParams): Promise<Response> {
  return fetch(`${SERVER_URL}/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  })
}

export function getCurrentUser(): Promise<Response> {
  return getServerRequest('users/me')
}
