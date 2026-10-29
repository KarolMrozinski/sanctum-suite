package network

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"os"
	"time"
)

type PacketInspectionResult struct {
	Timestamp   string `json:"timestamp"`
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Action      string `json:"action"`
	Reason      string `json:"reason"`
}

type AirGappedGuard struct {
	Enforced bool
}

func NewAirGappedGuard(enforced bool) *AirGappedGuard {
	log.Printf("[Go-NetworkGuard] Initialized. Air-gap strict enforcement: %v", enforced)
	return &AirGappedGuard{Enforced: enforced}
}

func (g *AirGappedGuard) InspectConnectionAttempt(src, dest string) PacketInspectionResult {
	log.Printf("[Go-NetworkGuard] Inspecting connection from %s to %s", src, dest)

	action := "ALLOW"
	reason := "Local loopback or internal IPC traffic permitted."

	// W trybie restrykcyjnym Air-Gapped blokujemy ruch wychodzący do zewnętrznych adresów IP
	if g.Enforced {
		parsedIP := net.ParseIP(dest)
		if parsedIP != nil && !parsedIP.IsLoopback() && !parsedIP.IsPrivate() {
			action = "BLOCK"
			reason = "Violation of Air-Gapped policy: external non-private IP detected."
		}
	}

	result := PacketInspectionResult{
		Timestamp:   time.Now().UTC().Format(time.RFC3339),
		Source:      src,
		Destination: dest,
		Action:      action,
		Reason:      reason,
	}

	return result
}

func (g *AirGappedGuard) LogInspectionToJson(result PacketInspectionResult, outputPath string) error {
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(outputPath, data, 0644)
}