// coordinator_agent invokes multiple worker targets in parallel and combines their results.
//
// Run:
//
//	go run ./scenarios/parallel_execution/coordinator_agent
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

type AnalyzeRequest struct {
	Text string `json:"text"`
}

type AnalysisResult struct {
	Agent string `json:"agent"`
	Text  string `json:"text"`
}

type invokeResult struct {
	target string
	result AnalysisResult
	err    error
}

func main() {
	agentId := "coordinator-agent"
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

	req := AnalyzeRequest{
		Text: "OpenAgentIO helps agents communicate with each other.",
	}
	targets := []string{"summary-agent", "sentiment-agent", "keywords-agent"}

	fmt.Println("[coordinator-agent] invoking workers in parallel")
	fmt.Printf("[coordinator-agent] input: %s\n", req.Text)

	results := make(chan invokeResult, len(targets))
	for _, target := range targets {
		go invokeWorker(ctx, b, target, req, results)
	}

	summary := make(map[string]string, len(targets))
	for range targets {
		out := <-results
		if out.err != nil {
			fmt.Fprintf(os.Stderr, "%s failed: %v\n", out.target, out.err)
			os.Exit(1)
		}
		summary[out.result.Agent] = out.result.Text
	}

	fmt.Println("[coordinator-agent] combined result:")
	for _, target := range targets {
		fmt.Printf("  %s: %s\n", target, summary[target])
	}
}

func invokeWorker(ctx context.Context, b bus.Bus, target string, req AnalyzeRequest, results chan<- invokeResult) {
	resp, err := b.Invoke(ctx, target, req, bus.WithTimeout(10*time.Second))
	if err != nil {
		results <- invokeResult{target: target, err: err}
		return
	}

	var result AnalysisResult
	if err := json.Unmarshal(resp.Payload, &result); err != nil {
		results <- invokeResult{target: target, err: fmt.Errorf("decode response: %w", err)}
		return
	}

	results <- invokeResult{target: target, result: result}
}
