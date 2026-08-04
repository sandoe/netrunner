package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		origin := r.Header.Get("Origin")
		if origin == "" {
			return true
		}
		parsed, err := url.Parse(origin)
		if err != nil {
			return false
		}
		requestHost := r.Host
		if host, _, err := net.SplitHostPort(requestHost); err == nil {
			requestHost = host
		}
		return strings.EqualFold(parsed.Hostname(), requestHost)
	},
}

var backendClient = &http.Client{Timeout: 5 * time.Second}

type AuthUser struct {
	Username string `json:"username"`
	Role     string `json:"role"`
}

type NodeCreds struct {
	ID        string `json:"id"`
	Host      string `json:"host"`
	Port      int    `json:"port"`
	Transport string `json:"transport"`
	Username  string `json:"username"`
	Password  string `json:"password"`
}

// WsMsg matches the protocol the frontend Terminal expects:
//   server -> client: {type:"output",data} | {type:"status",connected} | {type:"error",data}
//   client -> server: {type:"input",data}  | {type:"resize",cols,rows}
type WsMsg struct {
	Type      string `json:"type"`
	Data      string `json:"data,omitempty"`
	Connected bool   `json:"connected,omitempty"`
	Cols      int    `json:"cols,omitempty"`
	Rows      int    `json:"rows,omitempty"`
}

func fetchCredentials(nodeID string) (*NodeCreds, error) {
	// The Python backend is typically running on port 8000
	backendHost := os.Getenv("BACKEND_HOST")
	if backendHost == "" {
		backendHost = "http://backend:8000"
	}
	url := fmt.Sprintf("%s/api/internal/node/%s", backendHost, nodeID)

	internalToken := os.Getenv("NETRUNNER_INTERNAL_TOKEN")
	if internalToken == "" {
		return nil, fmt.Errorf("NETRUNNER_INTERNAL_TOKEN is not configured")
	}

	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-Netrunner-Internal-Token", internalToken)

	resp, err := backendClient.Do(req)
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

func authenticate(token string) (*AuthUser, error) {
	if token == "" {
		return nil, fmt.Errorf("missing access token")
	}
	backendHost := os.Getenv("BACKEND_HOST")
	if backendHost == "" {
		backendHost = "http://backend:8000"
	}
	req, err := http.NewRequest(http.MethodGet, backendHost+"/api/auth/me", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := backendClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("authentication failed")
	}
	var user AuthUser
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}
	if user.Username == "" || (user.Role != "admin" && user.Role != "analyst") {
		return nil, fmt.Errorf("terminal access is not permitted")
	}
	return &user, nil
}

func handleTerminal(w http.ResponseWriter, r *http.Request) {
	if _, err := authenticate(r.URL.Query().Get("token")); err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}
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
		cols := r.URL.Query().Get("cols")
		rows := r.URL.Query().Get("rows")
		session, err = handleTelnet(creds, cols, rows)
	} else {
		sendError(fmt.Sprintf("Unsupported transport: %s", creds.Transport))
		return
	}

	if err != nil {
		sendError(fmt.Sprintf("Connection failed: %v", err))
		return
	}
	defer session.Close()

	// Tell the frontend the link is up (flips it from "ESTABLISHING" to CONNECTED).
	ws.WriteJSON(WsMsg{Type: "status", Connected: true})
	ws.WriteJSON(WsMsg{Type: "output", Data: "\r\n[MUX] Connected successfully via Go.\r\n"})

	// Channel to signal disconnects
	done := make(chan struct{}, 2) // buffered to avoid blocking

	// Read from remote, write to WebSocket
	go func() {
		buf := make([]byte, 8192)
		for {
			n, err := session.Read(buf)
			if n > 0 {
				ws.WriteJSON(WsMsg{Type: "output", Data: string(buf[:n])})
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

				// Handle local echo if the telnet session says the remote isn't echoing
				if telnetSess, ok := session.(*TelnetSession); ok {
					if telnetSess.NeedsLocalEcho() {
						ws.WriteJSON(WsMsg{Type: "output", Data: msg.Data})
						// Also ensure Enter key moves the cursor to next line
						if msg.Data == "\r" {
							ws.WriteJSON(WsMsg{Type: "output", Data: "\n"})
						}
					}
				}

			} else if msg.Type == "resize" {
				// Resize is supported in SSH PTY; telnet ignores it for now.
				if sshSession, ok := session.(*SSHSession); ok {
					sshSession.Resize(msg.Cols, msg.Rows)
				}
			}
		}
		done <- struct{}{}
	}()

	<-done
	ws.WriteJSON(WsMsg{Type: "status", Connected: false})
	ws.WriteJSON(WsMsg{Type: "output", Data: "\r\n[MUX] Connection closed.\r\n"})
}

func main() {
	http.HandleFunc("/ws/terminal", handleTerminal)

	port := "8081"
	log.Printf("Go Terminal Multiplexer listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
