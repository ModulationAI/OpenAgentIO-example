// main_agent is the client that initiates a stream call to the sub_agent.
//
// It simulates the orchestrator or an upstream agent that needs real-time
// token-by-token output from a downstream Sub Agent.
//
// Run:
//
//	go run ./examples/scene_example/demo/stream/main_agent
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
		Content:            "Hello, Streaming World!",
	}

	fmt.Println("========================================")
	fmt.Println("Demo: MainAgent <--stream-- SubAgent")
	fmt.Println("========================================")
	if err := runStream(b, msg); err != nil {
		fmt.Fprintf(os.Stderr, "stream demo failed: %v\n", err)
		os.Exit(1)
	}
}

func runStream(b bus.Bus, msg internal.DingTalkMessage) error {
	env := msg.ToEnvelope()
	fmt.Printf("\n[MainAgent] stream-invoking sub-agent-stream\n")
	fmt.Printf("  [MainAgent] dingtalk content: %q\n", msg.Content)

	stream, err := b.StreamInvoke(context.Background(), "sub-agent-stream", env,
		bus.WithTimeout(30*time.Second),
		bus.WithIdleTimeout(2*time.Second),
	)
	if err != nil {
		return fmt.Errorf("stream invoke failed: %w", err)
	}
	defer stream.Close()

	fmt.Println("\n[MainAgent] consuming stream frames from SubAgent...")
	for frame, err := range stream.Events() {
		if err != nil {
			return fmt.Errorf("stream error: %w", err)
		}
		fmt.Printf("  [MainAgent] frame Seq=%d Type=%s IsFinal=%v Payload=%s\n",
			frame.Seq, frame.EventType, frame.IsFinal, string(frame.Payload))
	}
	fmt.Println("[MainAgent] stream closed")
	return nil
}
