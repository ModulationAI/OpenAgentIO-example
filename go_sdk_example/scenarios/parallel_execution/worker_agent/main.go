// worker_agent registers multiple worker targets for the parallel execution demo.
//
// Run:
//
//	go run ./scenarios/parallel_execution/worker_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"

	example_internal "openagentio-example/internal"
)

type AnalyzeRequest struct {
	Text string `json:"text"`
}

type AnalysisResult struct {
	Agent string `json:"agent"`
	Text  string `json:"text"`
}

func main() {
	agentId := "worker-agent"
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

	handlers := map[string]bus.InvokeHandler{
		"summary-agent":   handleSummary,
		"sentiment-agent": handleSentiment,
		"keywords-agent":  handleKeywords,
	}
	for target, handler := range handlers {
		if err := b.HandleInvoke(target, handler); err != nil {
			fmt.Fprintf(os.Stderr, "register %s: %v\n", target, err)
			os.Exit(1)
		}
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handlers: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[worker-agents] listening for parallel requests")
	fmt.Println("[worker-agents] targets: summary-agent, sentiment-agent, keywords-agent")
	fmt.Println("[worker-agents] start the coordinator in another terminal:")
	fmt.Println("  go run ./scenarios/parallel_execution/coordinator_agent")
	fmt.Println("[worker-agents] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[worker-agents] shutting down")
}

func handleSummary(_ context.Context, e *event.Envelope) (any, error) {
	req, err := decodeRequest(e)
	if err != nil {
		return nil, err
	}

	fmt.Printf("\n[summary-agent] analyzing: %s\n", req.Text)
	return AnalysisResult{
		Agent: "summary-agent",
		Text:  "OpenAgentIO connects multiple agents.",
	}, nil
}

func handleSentiment(_ context.Context, e *event.Envelope) (any, error) {
	req, err := decodeRequest(e)
	if err != nil {
		return nil, err
	}

	fmt.Printf("\n[sentiment-agent] analyzing: %s\n", req.Text)
	return AnalysisResult{
		Agent: "sentiment-agent",
		Text:  "positive",
	}, nil
}

func handleKeywords(_ context.Context, e *event.Envelope) (any, error) {
	req, err := decodeRequest(e)
	if err != nil {
		return nil, err
	}

	fmt.Printf("\n[keywords-agent] analyzing: %s\n", req.Text)
	words := []string{"OpenAgentIO", "agents", "communication"}
	return AnalysisResult{
		Agent: "keywords-agent",
		Text:  strings.Join(words, ", "),
	}, nil
}

func decodeRequest(e *event.Envelope) (AnalyzeRequest, error) {
	var req AnalyzeRequest
	if err := json.Unmarshal(e.Payload, &req); err != nil {
		return req, fmt.Errorf("decode request: %w", err)
	}
	return req, nil
}
