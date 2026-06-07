// worker_agent accepts tasks and publishes completion events later.
//
// Run:
//
//	go run ./scenarios/async_task/worker_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"syscall"
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
	agentId := "task-worker"
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

	if err := b.HandleInvoke("task-worker", func(ctx context.Context, e *event.Envelope) (any, error) {
		return handleTask(ctx, b, tp, e)
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register task-worker: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[task-worker] listening for async tasks")
	fmt.Println("[task-worker] start the client in another terminal:")
	fmt.Println("  go run ./scenarios/async_task/task_agent")
	fmt.Println("[task-worker] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[task-worker] shutting down")
}

func handleTask(ctx context.Context, b bus.Bus, tp any, e *event.Envelope) (any, error) {
	var req TaskRequest
	if err := json.Unmarshal(e.Payload, &req); err != nil {
		return nil, fmt.Errorf("decode task request: %w", err)
	}

	taskID := e.EventID
	fmt.Printf("\n[task-worker] accepted task %s: %s\n", taskID, req.Input)

	go completeTask(ctx, b, tp, taskID, req)

	return TaskAccepted{
		TaskID: taskID,
		Status: "accepted",
	}, nil
}

func completeTask(ctx context.Context, b bus.Bus, tp any, taskID string, req TaskRequest) {
	time.Sleep(1500 * time.Millisecond)

	done := TaskCompleted{
		TaskID: taskID,
		Result: "finished: " + req.Input,
	}
	payload, err := json.Marshal(done)
	if err != nil {
		fmt.Fprintf(os.Stderr, "encode completed event: %v\n", err)
		return
	}

	env := event.New(event.TaskCompleted)
	env.From = "task-worker"
	env.CorrelationID = taskID
	env.Payload = payload

	if err := b.Publish(ctx, env); err != nil {
		fmt.Fprintf(os.Stderr, "publish completed event: %v\n", err)
		return
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for completed event: %v\n", err)
		return
	}
	fmt.Printf("[task-worker] completed task %s\n", taskID)
}
