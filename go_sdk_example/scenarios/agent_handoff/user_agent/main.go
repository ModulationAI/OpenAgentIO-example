// user_agent sends a question to router-agent and receives the specialist answer.
//
// Run:
//
//	go run ./scenarios/agent_handoff/user_agent
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
	HandledBy string `json:"handled_by"`
	Text      string `json:"text"`
}

func main() {
	agentId := "user-agent"
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

	question := Question{Text: "I need help with my invoice"}

	fmt.Println("[user-agent] invoking router-agent")
	fmt.Printf("[user-agent] question: %s\n", question.Text)

	resp, err := b.Invoke(ctx, "router-agent", question, bus.WithTimeout(10*time.Second))
	if err != nil {
		fmt.Fprintf(os.Stderr, "invoke failed: %v\n", err)
		os.Exit(1)
	}

	var answer Answer
	if err := json.Unmarshal(resp.Payload, &answer); err != nil {
		fmt.Fprintf(os.Stderr, "decode response: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("[user-agent] response from %s: %s\n", answer.HandledBy, answer.Text)
}
