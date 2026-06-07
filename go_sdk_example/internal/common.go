// Package internal provides shared utilities for the scene_example demos.
package example_internal


// WaitForDemoTransport waits for asynchronous transport operations to reach
// the broker in short-lived command-line demos. Long-running applications
// usually do not need this synchronization point.
func WaitForDemoTransport(tp any) error {
	flusher, ok := tp.(interface{ Flush() error })
	if !ok {
		return nil
	}
	return flusher.Flush()
}
