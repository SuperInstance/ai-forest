package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
)

// AgentConfig holds configuration for the forest floor agent.
type AgentConfig struct {
	// WatchDir is the directory to monitor for file changes.
	WatchDir string

	// AgentName is the agent identifier used in the PLATO room path.
	AgentName string

	// Interval is the time between tile submissions.
	Interval time.Duration

	// ServerURL is the base PLATO-compatible server URL.
	ServerURL string
}

// DefaultConfig returns a default agent configuration.
func DefaultConfig() AgentConfig {
	return AgentConfig{
		WatchDir:  ".",
		AgentName: "oracle1",
		Interval:  10 * time.Second,
		ServerURL: "http://localhost:8847",
	}
}

// FileState tracks previous file sizes for delta computation.
type FileState struct {
	mu     sync.Mutex
	sizes  map[string]int64
	total  int64
}

// NewFileState creates a new FileState.
func NewFileState() *FileState {
	return &FileState{
		sizes: make(map[string]int64),
	}
}

// RecordChange records a file size change and returns the gradient (0.0-1.0),
// the absolute delta, and the new total size.
func (fs *FileState) RecordChange(path string, newSize int64) (gradient float64, delta int64, total int64) {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	oldSize := fs.sizes[path]
	delta = newSize - oldSize
	if delta < 0 {
		delta = -delta
	}
	fs.sizes[path] = newSize

	// Recompute total
	fs.total = 0
	for _, s := range fs.sizes {
		fs.total += s
	}
	total = fs.total

	if total == 0 {
		return 0, delta, 0
	}

	// Gradient = ratio of absolute change to total size
	gradient = float64(delta) / float64(total)
	if gradient > 1.0 {
		gradient = 1.0
	}
	return gradient, delta, total
}

// TilePayload is the JSON structure sent to the PLATO server.
type TilePayload struct {
	Agent    string `json:"agent"`
	Tile     uint32 `json:"tile"`
	Scheme   uint8  `json:"scheme"`
	RawGrad  uint8  `json:"raw_gradient"`
	RawConf  uint8  `json:"raw_confidence"`
	RawEps   uint8  `json:"raw_epsilon"`
	RawCtx   uint8  `json:"raw_context"`
}

// submitTile sends a tile to the PLATO-compatible server.
func submitTile(url string, payload TilePayload) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal error: %w", err)
	}

	resp, err := http.Post(url, "application/json", bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("post error: %w", err)
	}
	defer resp.Body.Close()

	// Read body for diagnostics
	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("server returned %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// gradientConfidence computes a confidence estimate based on how many files
// are being tracked (more files = higher confidence in gradient).
func gradientConfidence(fileCount int) float64 {
	if fileCount == 0 {
		return 0.0
	}
	// Confidence increases with file count, maxing out at 30+ files
	conf := float64(fileCount) / 30.0
	if conf > 1.0 {
		conf = 1.0
	}
	return conf
}

// gradientEpsilon computes a noise/uncertainty metric inversely related to
// tracked file count.
func gradientEpsilon(fileCount int) float64 {
	if fileCount == 0 {
		return 1.0
	}
	eps := 1.0 / float64(fileCount)
	if eps > 1.0 {
		eps = 1.0
	}
	return eps
}

// contextValue computes a simple context value based on the number of
// changes seen in the current cycle.
func contextValue(changeCount int) float64 {
	if changeCount > 15 {
		return 1.0
	}
	return float64(changeCount) / 15.0
}

// agentLoop runs the main agent cycle.
func agentLoop(cfg AgentConfig) error {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return fmt.Errorf("fsnotify watcher error: %w", err)
	}
	defer watcher.Close()

	// Add watch directory (recursively if possible, or just the directory itself)
	absDir, err := filepath.Abs(cfg.WatchDir)
	if err != nil {
		return fmt.Errorf("abs path error: %w", err)
	}

	// Walk the directory and add all subdirectories
	err = filepath.Walk(absDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return watcher.Add(path)
		}
		return nil
	})
	if err != nil {
		return fmt.Errorf("walk/add watch error: %w", err)
	}

	state := NewFileState()
	ticker := time.NewTicker(cfg.Interval)
	defer ticker.Stop()

	// Channel to accumulate changes between ticks
	type change struct {
		path    string
		newSize int64
	}
	changeCh := make(chan change, 100)

	// Goroutine to drain watcher events
	go func() {
		for {
			select {
			case event, ok := <-watcher.Events:
				if !ok {
					return
				}
				// Only process write and create events
				if event.Op&(fsnotify.Write|fsnotify.Create) != 0 {
					info, err := os.Stat(event.Name)
					if err != nil {
						continue // file may have been deleted
					}
					changeCh <- change{path: event.Name, newSize: info.Size()}
				}
			case err, ok := <-watcher.Errors:
				if !ok {
					return
				}
				log.Printf("watcher error: %v", err)
			}
		}
	}()

	log.Printf("🔮 Forest floor agent '%s' watching %s (interval: %v)",
		cfg.AgentName, absDir, cfg.Interval)

	for {
		select {
		case <-ticker.C:
			// Drain all pending changes from the channel
			pendingChanges := 0
			var latestGradient float64
			var latestDelta int64
			var latestTotal int64

		drainLoop:
			for {
				select {
				case ch := <-changeCh:
					grad, delta, total := state.RecordChange(ch.path, ch.newSize)
					latestGradient = grad
					latestDelta = delta
					latestTotal = total
					pendingChanges++
				default:
					break drainLoop
				}
			}

			fileCount := 0
			state.mu.Lock()
			fileCount = len(state.sizes)
			state.mu.Unlock()

			if pendingChanges == 0 {
				log.Printf("[%s] cycle: 0 changes, watching %d files",
					cfg.AgentName, fileCount)
				continue
			}

			// Build tile
			conf := gradientConfidence(fileCount)
			eps := gradientEpsilon(fileCount)
			ctx := contextValue(pendingChanges)

			tile := NewBalancedTile(conf, latestGradient, eps, ctx)
			packed, err := tile.Pack()
			if err != nil {
				log.Printf("[%s] tile pack error: %v", cfg.AgentName, err)
				continue
			}

			// Submit
			payload := TilePayload{
				Agent:   cfg.AgentName,
				Tile:    packed,
				Scheme:  tile.Scheme,
				RawGrad: tile.Gradient,
				RawConf: tile.Confidence,
				RawEps:  tile.Epsilon,
				RawCtx:  tile.Context,
			}

			roomURL := fmt.Sprintf("%s/room/floor-%s/submit", cfg.ServerURL, cfg.AgentName)
			if err := submitTile(roomURL, payload); err != nil {
				log.Printf("[%s] submit error: %v", cfg.AgentName, err)
			} else {
				log.Printf("[%s] submitted tile %s | delta=%d total=%d changes=%d files=%d",
					cfg.AgentName, tile, latestDelta, latestTotal, pendingChanges, fileCount)
			}
		}
	}
}

func main() {
	cfg := DefaultConfig()

	// Override from environment
	if v := os.Getenv("FLOOR_WATCH_DIR"); v != "" {
		cfg.WatchDir = v
	}
	if v := os.Getenv("FLOOR_AGENT_NAME"); v != "" {
		customDir := filepath.Join(cfg.WatchDir, v)
		if info, err := os.Stat(customDir); err == nil && info.IsDir() {
			cfg.WatchDir = customDir
		}
		cfg.AgentName = v
	}
	if v := os.Getenv("FLOOR_INTERVAL"); v != "" {
		d, err := time.ParseDuration(v)
		if err == nil {
			cfg.Interval = d
		}
	}
	if v := os.Getenv("FLOOR_SERVER_URL"); v != "" {
		cfg.ServerURL = v
	}

	log.Printf("🔮 Forest Floor Agent — %s", cfg.AgentName)
	log.Printf("   Watch Dir:  %s", cfg.WatchDir)
	log.Printf("   Interval:   %v", cfg.Interval)
	log.Printf("   Server URL: %s", cfg.ServerURL)

	if err := agentLoop(cfg); err != nil {
		log.Fatalf("agent error: %v", err)
	}
}
