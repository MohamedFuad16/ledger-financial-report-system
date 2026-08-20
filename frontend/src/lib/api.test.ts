import { describe, expect, it } from 'vitest'
import { consumeEventStream } from './api'

describe('consumeEventStream', () => {
  it('parses fragmented named SSE events', async () => {
    const encoder = new TextEncoder()
    const chunks = [
      'event: progress\ndata: {"step":"ext',
      'ract"}\n\nevent: batch_done\ndata: {"succeeded":1}\n\n',
    ]
    const stream = new ReadableStream({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
        controller.close()
      },
    })
    const response = new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
    const events: Array<{ event: string; data: unknown }> = []
    await consumeEventStream(response, (event) => events.push(event))
    expect(events).toEqual([
      { event: 'progress', data: { step: 'extract' } },
      { event: 'batch_done', data: { succeeded: 1 } },
    ])
  })

  it('surfaces a JSON API error before streaming', async () => {
    const response = new Response(JSON.stringify({ error: 'API key not configured.' }), { status: 400, headers: { 'Content-Type': 'application/json' } })
    await expect(consumeEventStream(response, () => undefined)).rejects.toThrow('API key not configured')
  })
})
