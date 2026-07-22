// The MV shape (STK-SWIFT-05): logic in an @Observable model, dependencies via init,
// fully testable under swift test with no UI and no simulator. A SwiftUI view binds
// to this with @State: `@State private var model = CounterModel(step: 5)`.
import Observation

@Observable
public final class CounterModel {
    public private(set) var count: Int
    public let step: Int
    public let range: ClosedRange<Int>

    /// Dependencies through init — no singletons, no hidden state (STK-SWIFT-05).
    public init(count: Int = 0, step: Int = 1, range: ClosedRange<Int> = 0...100) {
        precondition(step > 0, "step must be positive")
        self.count = range.contains(count) ? count : range.lowerBound
        self.step = step
        self.range = range
    }

    public var canIncrement: Bool { count + step <= range.upperBound }
    public var canDecrement: Bool { count - step >= range.lowerBound }

    public func increment() {
        guard canIncrement else { return }
        count += step
    }

    public func decrement() {
        guard canDecrement else { return }
        count -= step
    }

    public func reset() {
        count = range.lowerBound
    }
}
