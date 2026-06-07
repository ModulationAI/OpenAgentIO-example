// tool_agent exposes local Go functions through tool-agent.
//
// Run:
//
//	go run ./scenarios/function_calling/tool_agent
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

type FunctionCall struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

type FunctionResult struct {
	Name   string `json:"name"`
	Result any    `json:"result"`
}

type toolFunc func(map[string]any) (any, error)

func main() {
	agentId := "tool-agent"
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

	tools := map[string]toolFunc{
		"add_numbers":    addNumbers,
		"uppercase_text": uppercaseText,
	}

	if err := b.HandleInvoke("tool-agent", handleFunctionCall(tools)); err != nil {
		fmt.Fprintf(os.Stderr, "register tool-agent: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[tool-agent] listening for function calls")
	fmt.Println("[tool-agent] functions: add_numbers, uppercase_text")
	fmt.Println("[tool-agent] start the caller in another terminal:")
	fmt.Println("  go run ./scenarios/function_calling/caller_agent")
	fmt.Println("[tool-agent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[tool-agent] shutting down")
}

func handleFunctionCall(tools map[string]toolFunc) bus.InvokeHandler {
	return func(_ context.Context, e *event.Envelope) (any, error) {
		var call FunctionCall
		if err := json.Unmarshal(e.Payload, &call); err != nil {
			return nil, fmt.Errorf("decode function call: %w", err)
		}

		tool, ok := tools[call.Name]
		if !ok {
			return nil, fmt.Errorf("unknown function: %s", call.Name)
		}

		fmt.Printf("\n[tool-agent] calling %s with %v\n", call.Name, call.Arguments)
		result, err := tool(call.Arguments)
		if err != nil {
			return nil, err
		}

		return FunctionResult{
			Name:   call.Name,
			Result: result,
		}, nil
	}
}

func addNumbers(args map[string]any) (any, error) {
	a, err := numberArg(args, "a")
	if err != nil {
		return nil, err
	}
	b, err := numberArg(args, "b")
	if err != nil {
		return nil, err
	}

	return a + b, nil
}

func uppercaseText(args map[string]any) (any, error) {
	text, err := stringArg(args, "text")
	if err != nil {
		return nil, err
	}

	return strings.ToUpper(text), nil
}

func numberArg(args map[string]any, name string) (float64, error) {
	value, ok := args[name]
	if !ok {
		return 0, fmt.Errorf("missing argument %q", name)
	}

	switch v := value.(type) {
	case float64:
		return v, nil
	case int:
		return float64(v), nil
	default:
		return 0, fmt.Errorf("argument %q must be a number", name)
	}
}

func stringArg(args map[string]any, name string) (string, error) {
	value, ok := args[name]
	if !ok {
		return "", fmt.Errorf("missing argument %q", name)
	}

	text, ok := value.(string)
	if !ok {
		return "", fmt.Errorf("argument %q must be a string", name)
	}
	return text, nil
}
