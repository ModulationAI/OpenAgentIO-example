package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
	"github.com/ModulationAI/openagentio/pkg/middleware"

	internal "openagentio-example/internal"
)

func main() {
    agentName := "mainAgent"

	tp, err := transportdial.Dial(context.Background(), transportdial.WithNATSName(agentName))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}
	b, err := bus.New(
		bus.WithAgentID(agentName),
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

	msg := internal.DingTalkMessage{
		Sender:             "user_12345",
		ThreadID:           "thread_abc",
		OpenConversationID: "conv_67890",
		RunID:              "run_001",
		ConversationToken:  "token_xyz789",
		Content:            "Hello, Agentic World!",
	}

	fmt.Println("========================================")
	fmt.Println("Scenario 1: Request-Reply (sync invoke)")
	fmt.Println("========================================")
	if err := runInvoke(b, msg); err != nil {
		fmt.Fprintf(os.Stderr, "scenario 1 failed: %v\n", err)
		os.Exit(1)
	}

}

func runInvoke(b bus.Bus, msg internal.DingTalkMessage) error {
	env := msg.ToEnvelope()
	fmt.Printf("\n[AccessLayer] invoking main-agent\n")
	fmt.Printf("  [AccessLayer] dingtalk content: %q\n", msg.Content)

	resp, err := b.Invoke(context.Background(), "mainAgent", env, bus.WithTimeout(10*time.Second))
	if err != nil {
		return fmt.Errorf("invoke main-agent failed: %w", err)
	}

	fmt.Println("\n[AccessLayer] received final response")
	internal.PrintEnvelopeContext("AccessLayer", resp)
	fmt.Printf("  [AccessLayer] response payload: %s\n", string(resp.Payload))
	return nil
}
