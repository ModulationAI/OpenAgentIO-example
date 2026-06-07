// requester_agent sends a request to responder-agent and waits for one response.
//
// Run:
//
//	go run ./scenarios/request_reply/requester_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
)

type Question struct {
	Text string `json:"text"`
}

type Answer struct {
	Text string `json:"text"`
}

func main() {
	agentId := "requester-agent"
	ctx := context.Background()

	tp, err := transportdial.Dial(ctx, transportdial.WithNATSName(agentId))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}

	b, err := bus.New(
		bus.WithAgentID(agentId),
		bus.WithTransport(tp),
		bus.WithMiddleware(
			middleware.Recover(),
			middleware.Trace(),
		),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bus: %v\n", err)
		os.Exit(1)
	}
	defer b.Close()

	req := Question{Text: "hello from requester-agent"}

	fmt.Println("[requester-agent] invoking responder-agent")
	fmt.Printf("[requester-agent] request: %s\n", req.Text)

	resp, err := b.Invoke(ctx, "responder-agent", req, bus.WithTimeout(10*time.Second))
	if err != nil {
		fmt.Fprintf(os.Stderr, "invoke failed: %v\n", err)
		os.Exit(1)
	}

	var answer Answer
	if err := json.Unmarshal(resp.Payload, &answer); err != nil {
		fmt.Fprintf(os.Stderr, "decode response: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("[requester-agent] response: %s\n", answer.Text)
}
