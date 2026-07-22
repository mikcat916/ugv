window.DashboardRealtime = (() => {
  function clearTimers(state) {
    if (state.realtime.heartbeatTimer) {
      window.clearInterval(state.realtime.heartbeatTimer);
      state.realtime.heartbeatTimer = null;
    }
    if (state.realtime.reconnectTimer) {
      window.clearTimeout(state.realtime.reconnectTimer);
      state.realtime.reconnectTimer = null;
    }
  }

  function connect(state, onMessage) {
    if (typeof window.WebSocket === "undefined") return;
    const currentSocket = state.realtime.socket;
    if (currentSocket && (currentSocket.readyState === WebSocket.OPEN || currentSocket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    clearTimers(state);
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/dashboard`);
    state.realtime.socket = socket;

    const scheduleReconnect = () => {
      if (state.realtime.reconnectTimer) return;
      state.realtime.reconnectTimer = window.setTimeout(() => {
        state.realtime.reconnectTimer = null;
        connect(state, onMessage);
      }, 3000);
    };

    socket.addEventListener("open", () => {
      if (state.realtime.socket !== socket) return;
      state.realtime.heartbeatTimer = window.setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send("ping");
        }
      }, 20000);
    });

    socket.addEventListener("message", (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (error) {
        console.warn("实时消息解析失败。", error);
      }
    });

    socket.addEventListener("error", () => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    });

    socket.addEventListener("close", () => {
      if (state.realtime.socket === socket) {
        state.realtime.socket = null;
      }
      if (state.realtime.heartbeatTimer) {
        window.clearInterval(state.realtime.heartbeatTimer);
        state.realtime.heartbeatTimer = null;
      }
      scheduleReconnect();
    });
  }

  return { clearTimers, connect };
})();
