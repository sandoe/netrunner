package main

import (
	"fmt"
	"golang.org/x/crypto/ssh"
	"io"
	"time"
)

type SSHSession struct {
	client  *ssh.Client
	session *ssh.Session
	stdin   io.WriteCloser
	stdout  io.Reader
}

func handleSSH(creds *NodeCreds) (io.ReadWriteCloser, error) {
	config := &ssh.ClientConfig{
		User: creds.Username,
		Auth: []ssh.AuthMethod{
			ssh.Password(creds.Password),
		},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Timeout:         5 * time.Second,
	}

	addr := fmt.Sprintf("%s:%d", creds.Host, creds.Port)
	client, err := ssh.Dial("tcp", addr, config)
	if err != nil {
		return nil, fmt.Errorf("ssh dial failed: %v", err)
	}

	session, err := client.NewSession()
	if err != nil {
		client.Close()
		return nil, fmt.Errorf("failed to create session: %v", err)
	}

	modes := ssh.TerminalModes{
		ssh.ECHO:          1,
		ssh.TTY_OP_ISPEED: 14400,
		ssh.TTY_OP_OSPEED: 14400,
	}

	if err := session.RequestPty("xterm-256color", 50, 220, modes); err != nil {
		session.Close()
		client.Close()
		return nil, fmt.Errorf("failed to request pty: %v", err)
	}

	stdin, err := session.StdinPipe()
	if err != nil {
		return nil, err
	}

	stdout, err := session.StdoutPipe()
	if err != nil {
		return nil, err
	}
	// We want to multiplex stdout and stderr into the same stream
	session.Stderr = session.Stdout

	if err := session.Shell(); err != nil {
		return nil, fmt.Errorf("failed to start shell: %v", err)
	}

	return &SSHSession{
		client:  client,
		session: session,
		stdin:   stdin,
		stdout:  stdout,
	}, nil
}

func (s *SSHSession) Read(p []byte) (n int, err error) {
	return s.stdout.Read(p)
}

func (s *SSHSession) Write(p []byte) (n int, err error) {
	return s.stdin.Write(p)
}

func (s *SSHSession) Close() error {
	s.session.Close()
	return s.client.Close()
}

func (s *SSHSession) Resize(cols, rows int) {
	if cols > 0 && rows > 0 {
		s.session.WindowChange(rows, cols)
	}
}
