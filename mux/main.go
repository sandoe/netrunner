package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow cross-origin for dashboard
	},
}

type NodeCreds struct {
	ID        string `json:"id"`
	Host      string `json:"host"`
	Port      int    `json:"port"`
	Transport string `json:"transport"`
	Username  string `json:"username"`
	Password  string `json:"password"`
}

type WsMsg struct {
	Type string `json:"type"`
	Data string `json:"data"`
}

func fetchCredentials(nodeID string) (*NodeCreds, error) {
	// The Python backend is typically running on port 8000
	backendHost := os.Getenv("BACKEND_HOST")
	if backendHost == "" {
		backendHost = "http://backend:8000"
	}
	url := fmt.Sprintf("%s/api/internal/node/%s", backendHost, nodeID)

	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("backend returned status %d", resp.StatusCode)
	}

	var creds NodeCreds
	if err := json.NewDecoder(resp.Body).Decode(&creds); err != nil {
		return nil, err
	}
	return &creds, nil
}

func handleTerminal(w http.ResponseWriter, r *http.Request) {
	nodeID := r.URL.Query().Get("nodeId")
	if nodeID == "" {
		http.Error(w, "nodeId required", http.StatusBadRequest)
		return
	}

	ws, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("Upgrade error: %v", err)
		return
	}
	defer ws.Close()

	sendError := func(msg string) {
		ws.WriteJSON(WsMsg{Type: "error", Data: msg})
	}

	creds, err := fetchCredentials(nodeID)
	if err != nil {
		sendError(fmt.Sprintf("Failed to fetch credentials: %v", err))
		return
	}

	if creds.Host == "127.0.0.1" || creds.Host == "localhost" || creds.Host == "0.0.0.0" {
		creds.Host = "host.docker.internal"
	}

	var session io.ReadWriteCloser

	if creds.Transport == "ssh" {
		session, err = handleSSH(creds)
	} else if creds.Transport == "telnet" {
		session, err = handleTelnet(creds)
	} else {
		sendError(fmt.Sprintf("Unsupported transport: %s", creds.Transport))
		return
	}

	if err != nil {
		sendError(fmt.Sprintf("Connection failed: %v", err))
		return
	}
	defer session.Close()

	ws.WriteJSON(WsMsg{Type: "data", Data: "\r\n[MUX] Connected successfully via Go.\r\n"})

	// Channel to signal disconnects
	done := make(chan struct{}, 2) // buffered to avoid blocking

	// Read from remote, write to WebSocket
	go func() {
		buf := make([]byte, 8192)
		for {
			n, err := session.Read(buf)
			if n > 0 {
				ws.WriteJSON(WsMsg{Type: "data", Data: string(buf[:n])})
			}
			if err != nil {
				log.Printf("Remote read err: %v", err)
				break
			}
		}
		done <- struct{}{}
	}()

	// Read from WebSocket, write to remote
	go func() {
		for {
			var msg WsMsg
			err := ws.ReadJSON(&msg)
			if err != nil {
				log.Printf("WS read err: %v", err)
				break
			}
			if msg.Type == "data" || msg.Type == "input" {
				session.Write([]byte(msg.Data))
			} else if msg.Type == "resize" {
				// Resize is supported in SSH PTY, ignore in basic telnet for now
				if sshSession, ok := session.(*SSHSession); ok {
					var size struct{ Cols, Rows int }
					json.Unmarshal([]byte(msg.Data), &size)
					sshSession.Resize(size.Cols, size.Rows)
				}
			}
		}
		done <- struct{}{}
	}()

	<-done
	ws.WriteJSON(WsMsg{Type: "data", Data: "\r\n[MUX] Connection closed.\r\n"})
}

func main() {
	http.HandleFunc("/ws/terminal", handleTerminal)

	port := "8081"
	log.Printf("Go Terminal Multiplexer listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
