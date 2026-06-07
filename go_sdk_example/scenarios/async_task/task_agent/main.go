// task_agent submits a task and waits for its completion event.
//
// Run:
//
//	go run ./scenarios/async_task/task_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"

	example_internal "openagentio-example/internal"
)

type TaskRequest struct {
	Input string `json:"input"`
}

type TaskAccepted struct {
	TaskID string `json:"task_id"`
	Status string `json:"status"`
}

type TaskCompleted struct {
	TaskID string `json:"task_id"`
	Result string `json:"result"`
}

func main() {
	agentId := "task-client"
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

	completed := make(chan TaskCompleted, 8)
	sub, err := b.Subscribe(ctx, event.TaskCompleted, func(_ context.Context, e *event.Envelope) error {
		var done TaskCompleted
		if err := json.Unmarshal(e.Payload, &done); err != nil {
			return fmt.Errorf("decode completed event: %w", err)
		}
		completed <- done
		return nil
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "subscribe: %v\n", err)
		os.Exit(1)
	}
	defer sub.Unsubscribe()

	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for subscription: %v\n", err)
		os.Exit(1)
	}

	req := TaskRequest{Input: "generate a short report"}

	fmt.Println("[task-client] submitting task to task-worker")
	fmt.Printf("[task-client] input: %s\n", req.Input)

	resp, err := b.Invoke(ctx, "task-worker", req, bus.WithTimeout(10*time.Second))
	if err != nil {
		fmt.Fprintf(os.Stderr, "submit task failed: %v\n", err)
		os.Exit(1)
	}

	var accepted TaskAccepted
	if err := json.Unmarshal(resp.Payload, &accepted); err != nil {
		fmt.Fprintf(os.Stderr, "decode accepted response: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("[task-client] accepted: task_id=%s status=%s\n", accepted.TaskID, accepted.Status)
	fmt.Println("[task-client] waiting for completion event")

	timer := time.NewTimer(10 * time.Second)
	defer timer.Stop()

	for {
		select {
		case done := <-completed:
			if done.TaskID != accepted.TaskID {
				continue
			}
			fmt.Printf("[task-client] completed: task_id=%s result=%s\n", done.TaskID, done.Result)
			return
		case <-timer.C:
			fmt.Fprintln(os.Stderr, "timed out waiting for task completion")
			os.Exit(1)
		}
	}
}
