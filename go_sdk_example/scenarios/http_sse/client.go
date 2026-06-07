//go:build client

package main

// client is an optional low-level HTTP/SSE smoke test for the adapter.
// The recommended browser demo lives in ts_sdk_example/scenarios/sse_client.
// This command runs two protocol-level checks:
//
//   - invokeDemo:  synchronous request-reply (POST /v1/agents/echo/invoke).
//   - streamDemo:  SSE streaming (POST /v1/agents/count/stream).
//
// Start the server first:  go run -tags=server .
// Then run the client:  go run -tags=client .

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

const baseURL = "http://localhost:9080"

func main() {
	fmt.Println("=== Invoke Demo (POST /v1/agents/echo/invoke) ===")
	if err := invokeDemo(); err != nil {
		fmt.Fprintf(os.Stderr, "invoke failed: %v\n", err)
	}

	fmt.Println()
	fmt.Println("=== Stream Demo (POST /v1/agents/count/stream) ===")
	if err := streamDemo(); err != nil {
		fmt.Fprintf(os.Stderr, "stream failed: %v\n", err)
	}
}

// invokeDemo sends a JSON payload to the echo agent and prints the response.
func invokeDemo() error {
	payload := map[string]string{"msg": "hello from SSE client"}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	resp, err := http.Post(
		baseURL+"/v1/agents/echo/invoke",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	fmt.Printf("HTTP %d\n", resp.StatusCode)

	respBody, _ := io.ReadAll(resp.Body)
	fmt.Printf("Response: %s\n", respBody)
	return nil
}

// streamDemo opens an SSE connection to the count agent and prints each frame.
func streamDemo() error {
	payload := map[string]int{"n": 3}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", baseURL+"/v1/agents/count/stream", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status %d", resp.StatusCode)
	}

	// Parse SSE frames:  event: <type>\nid: <id>\ndata: <json>\n\n
	scanner := bufio.NewScanner(resp.Body)
	var (
		sseEvent string
		sseID    string
		sseData  string
		frameNum int
	)

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			// Blank line = end of SSE event, process what we collected.
			if sseEvent != "" {
				frameNum++
				fmt.Printf("\nFrame #%d  [%s]  id=%s\n", frameNum, sseEvent, sseID)
				fmt.Println("  Data:", sseData)
			}
			sseEvent = ""
			sseID = ""
			sseData = ""
			continue
		}

		if !strings.HasPrefix(line, "event: ") &&
			!strings.HasPrefix(line, "id: ") &&
			!strings.HasPrefix(line, "data: ") {
			continue
		}

		switch {
		case strings.HasPrefix(line, "event: "):
			sseEvent = strings.TrimPrefix(line, "event: ")
		case strings.HasPrefix(line, "id: "):
			sseID = strings.TrimPrefix(line, "id: ")
		case strings.HasPrefix(line, "data: "):
			sseData = strings.TrimPrefix(line, "data: ")
		}
	}
	if err := scanner.Err(); err != nil {
		return err
	}

	fmt.Printf("\nTotal frames received: %d\n", frameNum)
	return nil
}
