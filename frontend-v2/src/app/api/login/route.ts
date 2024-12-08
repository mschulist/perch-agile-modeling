import { NextRequest } from 'next/server'

const SERVER_URL = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  return fetch(`${SERVER_URL}/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: request.body,
    duplex: 'half',
  })
}
