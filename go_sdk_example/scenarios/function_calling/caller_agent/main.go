// caller_agent asks tool-agent to execute named functions.
//
// Run:
//
//	go run ./scenarios/function_calling/caller_agent
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

type FunctionCall struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

type FunctionResult struct {
	Name   string `json:"name"`
	Result any    `json:"result"`
}

func main() {
	agentId := "caller-agent"
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

	calls := []FunctionCall{
		{
			Name: "add_numbers",
			Arguments: map[string]any{
				"a": 7,
				"b": 5,
			},
		},
		{
			Name: "uppercase_text",
			Arguments: map[string]any{
				"text": "hello openagentio",
			},
		},
	}

	fmt.Println("[caller-agent] requesting function calls from tool-agent")
	for _, call := range calls {
		result, err := invokeFunction(ctx, b, call)
		if err != nil {
			fmt.Fprintf(os.Stderr, "call %s failed: %v\n", call.Name, err)
			os.Exit(1)
		}

		fmt.Printf("[caller-agent] %s -> %v\n", result.Name, result.Result)
	}
}

func invokeFunction(ctx context.Context, b bus.Bus, call FunctionCall) (FunctionResult, error) {
	resp, err := b.Invoke(ctx, "tool-agent", call, bus.WithTimeout(10*time.Second))
	if err != nil {
		return FunctionResult{}, err
	}

	var result FunctionResult
	if err := json.Unmarshal(resp.Payload, &result); err != nil {
		return FunctionResult{}, fmt.Errorf("decode response: %w", err)
	}
	return result, nil
}
