import { NextRequest } from 'next/server'

const SERVER_URL = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  const req = await request.json()
  const token = req.token
  const path = req.path
  return fetch(`${SERVER_URL}/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(req.body),
  })
}
