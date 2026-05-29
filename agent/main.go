package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/nxadm/tail"
)

type Event struct {
	Type     string `json:"type"`
	Severity string `json:"severity"`
	SourceIP string `json:"source_ip"`
}

var (
	targetURL string
	authToken string

	// Regexes ported from cti.py
	sshRe  = regexp.MustCompile(`Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+)`)
	webRe  = regexp.MustCompile(`^(\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(\S+)\s+(.*?)\s+HTTP/[^"]+"\s+(\d+)`)
	ufwRe  = regexp.MustCompile(`\[UFW BLOCK\].*?SRC=(\S+).*?DST=(\S+).*?DPT=(\d+)`)

	sqlPat  = regexp.MustCompile(`(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|' or 1=1|--|%27%20or%201%3D1|%20union%20select)`)
	pathPat = regexp.MustCompile(`(?i)(\.\./\.\.|/etc/passwd|/boot\.ini|win\.ini|%2e%2e%2f)`)
	xssPat  = regexp.MustCompile(`(?i)(<script>|javascript:|%3Cscript%3E|onerror=|onload=)`)
)

func main() {
	flag.StringVar(&targetURL, "target", "", "Netrunner API target URL (e.g., http://192.168.1.100:8000)")
	flag.StringVar(&authToken, "token", "", "Authentication token for the Netrunner API")
	flag.Parse()

	if targetURL == "" || authToken == "" {
		log.Fatal("Error: --target and --token are required.")
	}

	log.Printf("Starting Netrunner Agent...")
	log.Printf("Target: %s", targetURL)

	// Tail Auth logs
	go tailLog("/var/log/auth.log", parseSSHLog)

	// Tail Web logs
	go tailLog("/var/log/nginx/access.log", parseWebLog)
	go tailLog("/var/log/apache2/access.log", parseWebLog)
	go tailLog("/var/log/httpd/access_log", parseWebLog)

	// Tail Firewall logs
	go tailLog("/var/log/ufw.log", parseUFWLog)
	go tailLog("/var/log/syslog", parseUFWLog)

	// Keep main thread alive
	select {}
}

func tailLog(filepath string, parser func(string)) {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		log.Printf("File not found, skipping: %s", filepath)
		return
	}

	t, err := tail.TailFile(filepath, tail.Config{
		Follow:    true,
		ReOpen:    true,
		MustExist: false,
		Location:  &tail.SeekInfo{Offset: 0, Whence: os.SEEK_END}, // Start from EOF
	})

	if err != nil {
		log.Printf("Failed to tail %s: %v", filepath, err)
		return
	}

	log.Printf("Tailing: %s", filepath)
	for line := range t.Lines {
		parser(line.Text)
	}
}

func parseSSHLog(line string) {
	m := sshRe.FindStringSubmatch(line)
	if len(m) > 2 {
		username := m[1]
		ip := m[2]
		sendEvent(Event{
			Type:     fmt.Sprintf("SSH Brute Force (%s)", username),
			Severity: "high",
			SourceIP: ip,
		})
	}
}

func parseWebLog(line string) {
	m := webRe.FindStringSubmatch(line)
	if len(m) > 4 {
		ip := m[1]
		pathQuery := m[3]

		alertType := ""
		severity := "medium"

		if sqlPat.MatchString(pathQuery) {
			alertType = "SQL Injection Attempt"
			severity = "high"
		} else if pathPat.MatchString(pathQuery) {
			alertType = "Path Traversal Attempt"
			severity = "high"
		} else if xssPat.MatchString(pathQuery) {
			alertType = "XSS Attack Attempt"
			severity = "medium"
		}

		if alertType != "" {
			sendEvent(Event{
				Type:     alertType,
				Severity: severity,
				SourceIP: ip,
			})
		}
	}
}

func parseUFWLog(line string) {
	if !strings.Contains(line, "[UFW BLOCK]") {
		return
	}
	m := ufwRe.FindStringSubmatch(line)
	if len(m) > 3 {
		srcIP := m[1]
		port := m[3]
		sendEvent(Event{
			Type:     fmt.Sprintf("Port Scan (UFW Blocked Port %s)", port),
			Severity: "medium",
			SourceIP: srcIP,
		})
	}
}

func sendEvent(ev Event) {
	data, err := json.Marshal(ev)
	if err != nil {
		log.Printf("Error marshaling event: %v", err)
		return
	}

	req, err := http.NewRequest("POST", targetURL+"/api/agent/events", bytes.NewBuffer(data))
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+authToken)

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Failed to send event: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Warning: Target returned status %d", resp.StatusCode)
	}
}
