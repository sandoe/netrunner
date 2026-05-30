package main

import (
	"bytes"
	"fmt"
	"io"
	"net"
	"time"
)

const (
	IAC  = 255
	DONT = 254
	DO   = 253
	WONT = 252
	WILL = 251
)

type TelnetSession struct {
	conn net.Conn
}

func handleTelnet(creds *NodeCreds) (io.ReadWriteCloser, error) {
	addr := fmt.Sprintf("%s:%d", creds.Host, creds.Port)
	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return nil, fmt.Errorf("telnet dial failed: %v", err)
	}

	session := &TelnetSession{conn: conn}
	
	// Send basic negotiation (WILL Terminal Type, WILL Negotiate Window Size)
	// For simplicity in this basic mux, we just let the telnet scanner handle incoming IACs.
	
	return session, nil
}

func (s *TelnetSession) Read(p []byte) (n int, err error) {
	// A real telnet client parses IAC commands out of the stream.
	// For this mux, we will do a basic pass-through but strip IAC sequences.
	buf := make([]byte, len(p))
	n, err = s.conn.Read(buf)
	if err != nil {
		return 0, err
	}

	var out bytes.Buffer
	for i := 0; i < n; i++ {
		if buf[i] == IAC {
			// Telnet IAC sequence is typically 3 bytes (IAC DO/DONT/WILL/WONT OPTION)
			if i+2 < n {
				cmd := buf[i+1]
				opt := buf[i+2]
				
				// Automatically reject everything to prevent remote from hanging waiting for response
				var replyCmd byte
				if cmd == DO {
					replyCmd = WONT
				} else if cmd == WILL {
					replyCmd = DONT
				}
				
				if replyCmd != 0 {
					s.conn.Write([]byte{IAC, replyCmd, opt})
				}
				i += 2 // skip the next two bytes
				continue
			} else if i+1 < n && buf[i+1] == IAC {
				// Escaped IAC
				out.WriteByte(IAC)
				i++
				continue
			}
		} else {
			out.WriteByte(buf[i])
		}
	}
	
	copy(p, out.Bytes())
	return out.Len(), nil
}

func (s *TelnetSession) Write(p []byte) (n int, err error) {
	// Replace \n with \r\n if needed, but xterm.js usually sends \r
	return s.conn.Write(p)
}

func (s *TelnetSession) Close() error {
	return s.conn.Close()
}
