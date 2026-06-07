// handoff-agents registers router-agent and specialist targets for handoff.
//
// Run:
//
//	go run ./scenarios/agent_handoff/handoff-agents
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"

	example_internal "openagentio-example/internal"
)

type Question struct {
	Text string `json:"text"`
}

type Answer struct {
	HandledBy string `json:"handled_by"`
	Text      string `json:"text"`
}

func main() {
	agentId := "handoff-agents"
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

	if err := b.HandleInvoke("router-agent", func(ctx context.Context, e *event.Envelope) (any, error) {
		return handleRouter(ctx, b, e)
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register router-agent: %v\n", err)
		os.Exit(1)
	}
	if err := b.HandleInvoke("billing-agent", handleBilling); err != nil {
		fmt.Fprintf(os.Stderr, "register billing-agent: %v\n", err)
		os.Exit(1)
	}
	if err := b.HandleInvoke("tech-agent", handleTech); err != nil {
		fmt.Fprintf(os.Stderr, "register tech-agent: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handlers: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[handoff-agents] listening for handoff requests")
	fmt.Println("[handoff-agents] targets: router-agent, billing-agent, tech-agent")
	fmt.Println("[handoff-agents] start the user in another terminal:")
	fmt.Println("  go run ./scenarios/agent_handoff/user_agent")
	fmt.Println("[handoff-agents] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[handoff-agents] shutting down")
}

func handleRouter(ctx context.Context, b bus.Bus, e *event.Envelope) (any, error) {
	question, err := decodeQuestion(e)
	if err != nil {
		return nil, err
	}

	target := chooseTarget(question.Text)
	fmt.Printf("\n[router-agent] handoff to %s for: %s\n", target, question.Text)

	resp, err := b.Invoke(ctx, target, question, bus.WithTimeout(5*time.Second))
	if err != nil {
		return nil, fmt.Errorf("handoff to %s failed: %w", target, err)
	}

	var answer Answer
	if err := json.Unmarshal(resp.Payload, &answer); err != nil {
		return nil, fmt.Errorf("decode handoff response: %w", err)
	}
	return answer, nil
}

func handleBilling(_ context.Context, e *event.Envelope) (any, error) {
	question, err := decodeQuestion(e)
	if err != nil {
		return nil, err
	}

	fmt.Printf("[billing-agent] handling: %s\n", question.Text)
	return Answer{
		HandledBy: "billing-agent",
		Text:      "Billing can help with invoice and payment questions.",
	}, nil
}

func handleTech(_ context.Context, e *event.Envelope) (any, error) {
	question, err := decodeQuestion(e)
	if err != nil {
		return nil, err
	}

	fmt.Printf("[tech-agent] handling: %s\n", question.Text)
	return Answer{
		HandledBy: "tech-agent",
		Text:      "Tech support can help troubleshoot API and integration issues.",
	}, nil
}

func chooseTarget(text string) string {
	lower := strings.ToLower(text)
	if strings.Contains(lower, "invoice") ||
		strings.Contains(lower, "billing") ||
		strings.Contains(lower, "payment") {
		return "billing-agent"
	}
	return "tech-agent"
}

func decodeQuestion(e *event.Envelope) (Question, error) {
	var question Question
	if err := json.Unmarshal(e.Payload, &question); err != nil {
		return question, fmt.Errorf("decode question: %w", err)
	}
	return question, nil
}
