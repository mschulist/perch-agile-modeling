const SERVER_URL = process.env.SERVER_URL || 'http://localhost:8000'

export function getServerRequest(path: string): Promise<Response> {
  const token = localStorage.getItem('token')
  return fetch(`${SERVER_URL}/${path}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  })
}

export function postServerRequest(
  path: string,
  body: unknown
): Promise<Response> {
  const token = localStorage.getItem('token')
  return fetch(`${SERVER_URL}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
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

// TODO: make sure this is the correct server URL and check that it is not
// already a gs url (then we would not want to prepend the server URL)
export function getUrl(path: string) {
  const serverUrl = process.env.SERVER_URL || 'http://localhost:8000'
  if (path.startsWith('gs://')) {
    return path
  }
  return `${serverUrl}/get_file?filename=${path}`
}
