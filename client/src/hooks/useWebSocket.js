import { useEffect, useRef, useCallback } from "react";

export function useWebSocket(url, handlers) {
  const wsRef = useRef(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const handler = handlersRef.current[msg.event];
        if (handler) handler(msg.data);
      } catch (err) {
        console.error("WS parse error", err);
      }
    };

    ws.onclose = () => {
      // Reconnect after 3s
      setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [url]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);
}
