package main

import (
	"bytes"
	"encoding/binary"
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
	"github.com/cilium/ebpf/ringbuf"
	"golang.org/x/sys/unix"

	"netrunner-agent/bpf"
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

	// Start eBPF DPI
	go startDPI()

	// Keep main thread alive
	select {}
}

func htons(i uint16) uint16 {
	return (i<<8)&0xff00 | i>>8
}

type bpfEvent struct {
	Saddr            uint32
	Daddr            uint32
	Sport            uint16
	Dport            uint16
	RuleId           uint32
}

type ApiRule struct {
	ID        uint32 `json:"id"`
	Name      string `json:"name"`
	Port      uint16 `json:"port"`
	Signature string `json:"signature"`
	Severity  string `json:"severity"`
}

type ApiRulesResponse struct {
	Rules []ApiRule `json:"rules"`
}

var activeRules = make(map[uint32]ApiRule)

func loadRules(objs *bpf.DpiObjects) {
	client := &http.Client{Timeout: 5 * time.Second}
	req, err := http.NewRequest("GET", targetURL+"/api/rules/active", nil)
	if err != nil {
		log.Printf("Failed to create rules request: %v", err)
		return
	}

	req.Header.Set("Authorization", "Bearer "+authToken)
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Failed to fetch rules: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Non-OK response fetching rules: %v", resp.Status)
		return
	}

	var rulesResp ApiRulesResponse
	if err := json.NewDecoder(resp.Body).Decode(&rulesResp); err != nil {
		log.Printf("Failed to decode rules: %v", err)
		return
	}

	// Update maps
	for i, rule := range rulesResp.Rules {
		activeRules[rule.ID] = rule

		var sig [8]uint8
		sigLen := len(rule.Signature)
		if sigLen > 8 {
			sigLen = 8
		}
		for j := 0; j < sigLen; j++ {
			sig[j] = rule.Signature[j]
		}

		bpfRule := bpf.DpiRule{
			RuleId:    rule.ID,
			Dport:     rule.Port,
			SigLen:    uint16(sigLen),
			Signature: sig,
		}

		if err := objs.RulesMap.Put(uint32(i), bpfRule); err != nil {
			log.Printf("Failed to load rule %d into BPF map: %v", rule.ID, err)
		}
	}
	log.Printf("Loaded %d DPI rules into BPF Map.", len(rulesResp.Rules))
}

func startDPI() {
	var objs bpf.DpiObjects
	if err := bpf.LoadDpiObjects(&objs, nil); err != nil {
		log.Printf("Failed to load eBPF objects: %v. Are you running as root?", err)
		return
	}
	defer objs.Close()

	// Load dynamic rules into map
	loadRules(&objs)

	sock, err := unix.Socket(unix.AF_PACKET, unix.SOCK_RAW, int(htons(unix.ETH_P_ALL)))
	if err != nil {
		log.Printf("Failed to create raw socket: %v", err)
		return
	}
	defer unix.Close(sock)

	if err := unix.SetsockoptInt(sock, unix.SOL_SOCKET, unix.SO_ATTACH_BPF, objs.SocketDpi.FD()); err != nil {
		log.Printf("Failed to attach BPF to socket: %v", err)
		return
	}

	rb, err := ringbuf.NewReader(objs.Events)
	if err != nil {
		log.Printf("Failed to open ringbuf: %v", err)
		return
	}
	defer rb.Close()

	log.Printf("eBPF DPI started.")

	for {
		rec, err := rb.Read()
		if err != nil {
			log.Printf("Ringbuf read error: %v", err)
			continue
		}

		var ev bpfEvent
		if err := binary.Read(bytes.NewBuffer(rec.RawSample), binary.LittleEndian, &ev); err != nil {
			log.Printf("Failed to parse event: %v", err)
			continue
		}

		// Lookup rule
		rule, ok := activeRules[ev.RuleId]
		if !ok {
			log.Printf("Unknown rule ID matched: %d", ev.RuleId)
			continue
		}

		sendEvent(Event{
			Type:     fmt.Sprintf("eBPF DPI: %s", rule.Name),
			Severity: rule.Severity,
			SourceIP: fmt.Sprintf("%d.%d.%d.%d", ev.Saddr&0xff, (ev.Saddr>>8)&0xff, (ev.Saddr>>16)&0xff, ev.Saddr>>24),
		})
	}
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
