export function getServerRequest(path: string): Promise<Response> {
  const token = localStorage.getItem('token')
  return fetch('/api/getServerRequest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token,
      path,
    }),
  })
}

export function postServerRequest(
  path: string,
  body: unknown
): Promise<Response> {
  const token = localStorage.getItem('token')
  return fetch('/api/postServerRequest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token,
      path,
      body,
    }),
  })
}

export function loginRequest(formData: URLSearchParams): Promise<Response> {
  return fetch(`/api/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
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
  if (path.startsWith('https://storage.googleapis.com')) {
    return path
  }
  return `${serverUrl}/get_file?filename=${path}`
}
