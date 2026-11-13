package network

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type TelemetryEvent struct {
	EventID   string                 `json:"event_id"`
	Timestamp string                 `json:"timestamp"`
	EventType string                 `json:"event_type"`
	Payload   map[string]interface{} `json:"payload"`
}

type TelemetryDispatcher struct {
	mu         sync.Mutex
	bufferDir  string
	maxBatch   int
	events     []TelemetryEvent
}

func NewTelemetryDispatcher(bufferDir string, maxBatch int) (*TelemetryDispatcher, error) {
	if err := os.MkdirAll(bufferDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create telemetry buffer dir: %w", err)
	}

	log.Printf("[Go-Dispatcher] Initialized in directory: %s (Batch size: %d)", bufferDir, maxBatch)
	return &TelemetryDispatcher{
		bufferDir: bufferDir,
		maxBatch:  maxBatch,
		events:    make([]TelemetryEvent, 0, maxBatch),
	}, nil
}

func (d *TelemetryDispatcher) IngestEvent(eventType string, payload map[string]interface{}) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	event := TelemetryEvent{
		EventID:   fmt.Sprintf("EVT-%d", time.Now().UnixNano()),
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		EventType: eventType,
		Payload:   payload,
	}

	d.events = append(d.events, event)
	log.Printf("[Go-Dispatcher] Ingested event %s. Buffer count: %d/%d", event.EventID, len(d.events), d.maxBatch)

	if len(d.events) >= d.maxBatch {
		return d.flushLocked()
	}

	return nil
}

func (d *TelemetryDispatcher) flushLocked() error {
	if len(d.events) == 0 {
		return nil
	}

	filename := fmt.Sprintf("batch-%s.jsonl", time.Now().Format("20060102-150405"))
	filePath := filepath.Join(d.bufferDir, filename)

	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("failed to create batch file: %w", err)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	for _, ev := range d.events {
		if err := encoder.Encode(ev); err != nil {
			log.Printf("[Go-Dispatcher] Error encoding event: %v", err)
		}
	}

	log.Printf("[Go-Dispatcher] Flushed %d events to disk: %s", len(d.events), filePath)
	d.events = d.events[:0] // Reset bufora
	return nil
}