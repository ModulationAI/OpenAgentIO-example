// client sends a calculation request to gateway-agent and prints the trace.
//
// Run:
//
//	go run ./scenarios/otel_tracing/client
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	otelmiddleware "github.com/ModulationAI/openagentio/pkg/middleware/otel"
	transportdial "github.com/ModulationAI/openagentio/pkg/transport/dial"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.27.0"
	"go.opentelemetry.io/otel/trace"
)

type CalcRequest struct {
	A  int    `json:"a"`
	B  int    `json:"b"`
	Op string `json:"op"`
}

type CalcResponse struct {
	Result int    `json:"result"`
	Agent  string `json:"agent"`
}

func main() {
	shutdown := initTracer("otel-client")
	defer shutdown()

	ctx := context.Background()

	// Start a root span that will propagate through the entire call chain.
	tr := otel.Tracer("otel-client")
	ctx, span := tr.Start(ctx, "client.calc-request",
		trace.WithAttributes(
			attribute.Int("calc.a", 14),
			attribute.Int("calc.b", 3),
			attribute.String("calc.op", "add"),
		))
	defer span.End()

	// Print the TraceID so the user can look it up in Jaeger UI.
	sc := trace.SpanFromContext(ctx).SpanContext()
	if sc.IsValid() {
		fmt.Printf("[client] TraceID: %s\n", sc.TraceID().String())
	}

	tp, err := transportdial.Dial(ctx, transportdial.WithNATSName("otel-client"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}

	b, err := bus.New(
		bus.WithAgentID("otel-client"),
		bus.WithTransport(tp),
		bus.WithEnvelopePreparer(
			otelmiddleware.EnvelopePreparer(),
		),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bus: %v\n", err)
		os.Exit(1)
	}
	defer b.Close()

	req := CalcRequest{A: 14, B: 3, Op: "add"}
	fmt.Printf("[client] invoking gateway-agent with %d %s %d\n", req.A, req.Op, req.B)

	resp, err := b.Invoke(ctx, "gateway-agent", req, bus.WithTimeout(5*time.Second))
	if err != nil {
		span.RecordError(err)
		fmt.Fprintf(os.Stderr, "invoke failed: %v\n", err)
		os.Exit(1)
	}

	var result CalcResponse
	if err := json.Unmarshal(resp.Payload, &result); err != nil {
		fmt.Fprintf(os.Stderr, "decode response: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("[client] result=%d handled_by=%s\n", result.Result, result.Agent)
	fmt.Println("[client] open http://localhost:16686 and search by TraceID to view the trace")
}

func initTracer(serviceName string) func() {
	ctx := context.Background()

	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:4317"
	}

	exp, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(endpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		panic(fmt.Sprintf("failed to create OTLP exporter: %v", err))
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(serviceName),
		)),
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return func() {
		_ = tp.Shutdown(ctx)
	}
}
