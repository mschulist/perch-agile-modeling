import { NextRequest, NextResponse } from 'next/server'

const SERVER_URL = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  const req = await request.json()
  const token = req.token
  const path = req.path
  const res = await fetch(`${SERVER_URL}/${path}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  })
  if (res.status !== 200) {
    console.log('Failed to fetch data')
    return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 })
  }
  const data = await res.json()
  return NextResponse.json(data)
}
