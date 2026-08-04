package main

import (
	"bytes"
	"context"
	"crypto/subtle"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"strings"
	"time"

	"github.com/cilium/ebpf/ringbuf"
	"github.com/nxadm/tail"
	"go.bug.st/serial"
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
	nodeID    string

	// Regexes ported from cti.py
	sshRe = regexp.MustCompile(`Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+)`)
	webRe = regexp.MustCompile(`^(\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(\S+)\s+(.*?)\s+HTTP/[^"]+"\s+(\d+)`)
	ufwRe = regexp.MustCompile(`\[UFW BLOCK\].*?SRC=(\S+).*?DST=(\S+).*?DPT=(\d+)`)

	sqlPat  = regexp.MustCompile(`(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|' or 1=1|--|%27%20or%201%3D1|%20union%20select)`)
	pathPat = regexp.MustCompile(`(?i)(\.\./\.\.|/etc/passwd|/boot\.ini|win\.ini|%2e%2e%2f)`)
	xssPat  = regexp.MustCompile(`(?i)(<script>|javascript:|%3Cscript%3E|onerror=|onload=)`)
)

func main() {
	flag.StringVar(&targetURL, "target", "", "Netrunner API target URL (e.g., http://192.168.1.100:8000)")
	flag.StringVar(&authToken, "token", "", "Authentication token for the Netrunner API")
	flag.StringVar(&nodeID, "node", "", "Node ID for distributed tracking")
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

	// Start Bluetooth Scanner
	go startBluetoothScanner()

	// Start Serial / USB Monitoring
	go startSerialScanner()

	// Start local HTTP server for two-way comms (e.g., serial write)
	go startLocalServer()

	// Keep main thread alive
	select {}
}

func startLocalServer() {
	http.HandleFunc("/serial/write", func(w http.ResponseWriter, r *http.Request) {
		if !agentRequestAuthorized(r) {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req struct {
			Port string `json:"port"`
			Data string `json:"data"`
			Baud int    `json:"baud"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		if req.Baud == 0 {
			req.Baud = 115200
		}
		mode := &serial.Mode{
			BaudRate: req.Baud,
		}
		port, err := serial.Open(req.Port, mode)
		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to open port: %v", err), http.StatusInternalServerError)
			return
		}
		defer port.Close()

		_, err = port.Write([]byte(req.Data + "\n"))
		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to write to port: %v", err), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	log.Printf("Starting local agent control server on :8001")
	if err := http.ListenAndServe(":8001", nil); err != nil {
		log.Printf("Local server error: %v", err)
	}
}

func agentRequestAuthorized(r *http.Request) bool {
	const prefix = "Bearer "
	header := r.Header.Get("Authorization")
	if !strings.HasPrefix(header, prefix) || authToken == "" {
		return false
	}
	provided := strings.TrimSpace(strings.TrimPrefix(header, prefix))
	return subtle.ConstantTimeCompare([]byte(provided), []byte(authToken)) == 1
}

func htons(i uint16) uint16 {
	return (i<<8)&0xff00 | i>>8
}

type bpfEvent struct {
	Saddr  uint32
	Daddr  uint32
	Sport  uint16
	Dport  uint16
	RuleId uint32
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
		log.Printf("Failed to load eBPF objects: %v. Are you running as root? Skipping eBPF telemetry.", err)
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

func sendData(endpoint string, payload interface{}) (int, error) {
	data, err := json.Marshal(payload)
	if err != nil {
		return 0, fmt.Errorf("marshal error: %w", err)
	}

	req, err := http.NewRequest("POST", targetURL+endpoint, bytes.NewBuffer(data))
	if err != nil {
		return 0, fmt.Errorf("request error: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+authToken)
	if nodeID != "" {
		req.Header.Set("X-Node-ID", nodeID)
	}

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("client do error: %w", err)
	}
	defer resp.Body.Close()

	return resp.StatusCode, nil
}

func sendEvent(ev Event) {
	status, err := sendData("/api/agent/events", ev)
	if err != nil {
		log.Printf("Failed to send event: %v", err)
		return
	}
	if status != http.StatusOK {
		log.Printf("Warning: Target returned status %d", status)
	}
}

type BluetoothDevice struct {
	MAC  string `json:"mac"`
	RSSI int    `json:"rssi"`
	Name string `json:"name"`
}

type BluetoothReport struct {
	Devices []BluetoothDevice `json:"devices"`
}

func startBluetoothScanner() {
	// Pattern to match btmgmt find output
	btRe := regexp.MustCompile(`(?i)([0-9A-F]{2}(?::[0-9A-F]{2}){5}).*?rssi\s+(-?\d+)`)
	// Pattern for bluetoothctl devices
	ctlRe := regexp.MustCompile(`(?i)Device\s+([0-9A-F]{2}(?::[0-9A-F]{2}){5})\s+(.+)`)

	for {
		ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
		cmd := exec.CommandContext(ctx, "btmgmt", "find")
		out, err := cmd.CombinedOutput()
		cancel()
		outStr := string(out)

		log.Printf("BT Scanner ran btmgmt find, error: %v", err)

		devMap := make(map[string]BluetoothDevice)

		if err == nil || ctx.Err() == context.DeadlineExceeded {
			if !strings.Contains(outStr, "Busy") && !strings.Contains(outStr, "Not Powered") {
				lines := strings.Split(outStr, "\n")
				for _, line := range lines {
					m := btRe.FindStringSubmatch(line)
					if len(m) == 3 {
						mac := strings.ToUpper(m[1])
						var rssi int
						fmt.Sscanf(m[2], "%d", &rssi)
						devMap[mac] = BluetoothDevice{MAC: mac, RSSI: rssi, Name: "Unknown Device"}
					}
				}
			}
		}

		// Always supplement with bluetoothctl devices (which includes paired/known Classic devices)
		cmd = exec.Command("bluetoothctl", "devices")
		out, _ = cmd.CombinedOutput()
		lines := strings.Split(string(out), "\n")
		for _, line := range lines {
			m := ctlRe.FindStringSubmatch(line)
			if len(m) == 3 {
				mac := strings.ToUpper(m[1])
				name := strings.TrimSpace(m[2])

				if dev, exists := devMap[mac]; exists {
					// Update name if we only knew it from btmgmt
					if name != "" {
						dev.Name = name
						devMap[mac] = dev
					}
				} else {
					// New device from bluetoothctl
					if name == "" {
						name = "Unknown Device"
					}
					devMap[mac] = BluetoothDevice{MAC: mac, RSSI: 0, Name: name}
				}
			}
		}

		var devs []BluetoothDevice
		for _, dev := range devMap {
			devs = append(devs, dev)
		}

		if len(devs) > 0 {
			sendBluetoothReport(BluetoothReport{Devices: devs})
		}

		time.Sleep(3 * time.Second)
	}
}

func sendBluetoothReport(report BluetoothReport) {
	status, err := sendData("/api/agent/bluetooth", report)
	if err != nil {
		log.Printf("Error sending BT report: %v", err)
		return
	}
	log.Printf("Sent Bluetooth report with %d devices, status: %d", len(report.Devices), status)
}

func startSerialScanner() {
	log.Printf("Starting USB/Serial monitor...")
	knownPorts := make(map[string]bool)

	for {
		ports, err := serial.GetPortsList()
		if err != nil {
			log.Printf("Error listing serial ports: %v", err)
			time.Sleep(5 * time.Second)
			continue
		}

		// Find new ports
		currentPorts := make(map[string]bool)
		for _, portName := range ports {
			currentPorts[portName] = true
			if !knownPorts[portName] {
				log.Printf("New USB/Serial device detected: %s", portName)
				knownPorts[portName] = true

				// Send alert to mother ship
				sendEvent(Event{
					Type:     fmt.Sprintf("Hardware: USB/Serial Device Connected (%s)", portName),
					Severity: "high",
					SourceIP: "127.0.0.1",
				})

				// Start reading from the port in the background
				go readSerialPort(portName)
			}
		}

		// Cleanup disconnected ports
		for portName := range knownPorts {
			if !currentPorts[portName] {
				log.Printf("USB/Serial device disconnected: %s", portName)
				delete(knownPorts, portName)
				sendEvent(Event{
					Type:     fmt.Sprintf("Hardware: USB/Serial Device Disconnected (%s)", portName),
					Severity: "medium",
					SourceIP: "127.0.0.1",
				})
			}
		}

		// Periodically report all connected USB devices
		var usbDevices []map[string]string
		for portName := range knownPorts {
			usbDevices = append(usbDevices, map[string]string{
				"device": portName,
				"name":   "Serial Device",
			})
		}
		if len(usbDevices) > 0 {
			sendUSBReport(usbDevices)
		}

		time.Sleep(5 * time.Second)
	}
}

func sendUSBReport(devices []map[string]string) {
	payload := map[string]interface{}{
		"devices": devices,
	}
	_, err := sendData("/api/agent/usb", payload)
	if err != nil {
		log.Printf("Error sending USB report: %v", err)
	}
}

func readSerialPort(portName string) {
	mode := &serial.Mode{
		BaudRate: 115200,
	}
	port, err := serial.Open(portName, mode)
	if err != nil {
		log.Printf("Failed to open serial port %s: %v", portName, err)
		return
	}
	defer port.Close()

	buf := make([]byte, 256)
	for {
		n, err := port.Read(buf)
		if err != nil {
			log.Printf("Stopped reading from %s: %v", portName, err)
			break
		}
		if n > 0 {
			dataStr := strings.TrimSpace(string(buf[:n]))
			if len(dataStr) > 0 {
				log.Printf("Data from %s: %s", portName, dataStr)
				// Send specific strings to threat map
				sendEvent(Event{
					Type:     fmt.Sprintf("Serial Data [%s]: %s", portName, dataStr),
					Severity: "medium",
					SourceIP: "127.0.0.1",
				})
			}
		}
	}
}
