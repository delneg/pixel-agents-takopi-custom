/**
 * Communication adapter — WebSocket (webapp) or VS Code postMessage (extension).
 *
 * In webapp mode, messages go over a WebSocket to the Python backend.
 * Incoming messages are dispatched as 'message' events on window so that
 * the existing `window.addEventListener('message', handler)` pattern works.
 */

const IS_VSCODE = typeof acquireVsCodeApi === 'function'

let ws: WebSocket | null = null

function connectWebSocket(): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${window.location.host}/ws`
  const socket = new WebSocket(url)

  socket.onopen = () => {
    console.log('[WS] Connected')
  }

  socket.onmessage = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data as string)
      // Dispatch as a window 'message' event so useExtensionMessages works unchanged
      window.dispatchEvent(new MessageEvent('message', { data }))
    } catch (err) {
      console.error('[WS] Failed to parse message:', err)
    }
  }

  socket.onclose = () => {
    console.log('[WS] Disconnected, reconnecting in 2s...')
    ws = null
    setTimeout(() => {
      ws = connectWebSocket()
    }, 2000)
  }

  socket.onerror = (err) => {
    console.error('[WS] Error:', err)
  }

  return socket
}

interface VscodeApi {
  postMessage(msg: unknown): void
}

function createWebSocketApi(): VscodeApi {
  ws = connectWebSocket()
  return {
    postMessage(msg: unknown): void {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg))
      } else {
        console.warn('[WS] Not connected, message dropped:', msg)
      }
    },
  }
}

function createVscodeApi(): VscodeApi {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (acquireVsCodeApi as () => VscodeApi)()
}

export const vscode: VscodeApi = IS_VSCODE ? createVscodeApi() : createWebSocketApi()

/**
 * Whether we're running as a standalone webapp (WebSocket mode).
 */
export const IS_WEBAPP = !IS_VSCODE

// Declare acquireVsCodeApi so TypeScript doesn't error — it may not exist at runtime
declare function acquireVsCodeApi(): VscodeApi
