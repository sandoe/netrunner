package main

import (
	"bytes"
	"fmt"
	"io"
	"net"
	"sync"
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
	conn       net.Conn
	mu         sync.Mutex
	remoteWill map[byte]bool
	localWill  map[byte]bool
}

func handleTelnet(creds *NodeCreds, cols string, rows string) (io.ReadWriteCloser, error) {
	addr := fmt.Sprintf("%s:%d", creds.Host, creds.Port)
	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return nil, fmt.Errorf("telnet dial failed: %v", err)
	}

	session := &TelnetSession{
		conn:       conn,
		remoteWill: make(map[byte]bool),
		localWill:  make(map[byte]bool),
	}

	// Request the remote to ECHO and Suppress Go Ahead
	session.sendCmd(DO, 1) // ECHO
	session.sendCmd(DO, 3) // SGA
	session.sendCmd(WILL, 3) // SGA

	if cols == "" {
		cols = "120"
	}
	if rows == "" {
		rows = "40"
	}

	go func() {
		time.Sleep(200 * time.Millisecond) // Give the serial console a tiny bit of time
		initCmd := fmt.Sprintf("\r\nstty echo; stty rows %s cols %s 2>/dev/null; export TERM=xterm-256color; export PS1='\\h:\\w\\$ '; clear\r\n", rows, cols)
		session.Write([]byte(initCmd))
	}()

	return session, nil
}

func (s *TelnetSession) NeedsLocalEcho() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return !s.remoteWill[1]
}

func (s *TelnetSession) sendCmd(cmd, opt byte) {
	s.conn.Write([]byte{IAC, cmd, opt})
}

func (s *TelnetSession) Read(p []byte) (n int, err error) {
	buf := make([]byte, len(p))
	n, err = s.conn.Read(buf)
	if err != nil {
		return 0, err
	}

	var out bytes.Buffer
	for i := 0; i < n; i++ {
		if buf[i] == IAC {
			if i+2 < n {
				cmd := buf[i+1]
				opt := buf[i+2]

				s.handleOption(cmd, opt)
				i += 2
				continue
			} else if i+1 < n && buf[i+1] == IAC {
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

func (s *TelnetSession) handleOption(cmd byte, opt byte) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if cmd == WILL {
		if !s.remoteWill[opt] {
			s.remoteWill[opt] = true
			if opt == 1 || opt == 3 {
				s.sendCmd(DO, opt)
			} else {
				s.sendCmd(DONT, opt)
				s.remoteWill[opt] = false
			}
		}
	} else if cmd == DO {
		if !s.localWill[opt] {
			s.localWill[opt] = true
			if opt == 3 {
				s.sendCmd(WILL, opt)
			} else {
				s.sendCmd(WONT, opt)
				s.localWill[opt] = false
			}
		}
	} else if cmd == WONT {
		s.remoteWill[opt] = false
	} else if cmd == DONT {
		s.localWill[opt] = false
	}
}

func (s *TelnetSession) Write(p []byte) (n int, err error) {
	return s.conn.Write(p)
}

func (s *TelnetSession) Close() error {
	return s.conn.Close()
}
