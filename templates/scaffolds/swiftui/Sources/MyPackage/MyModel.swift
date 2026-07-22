// The MV shape (STK-SWIFT-05): logic in an @Observable model, dependencies via init,
// testable with no UI. Views bind to this via @State (owned) or @Environment (shared).
import Observation

@Observable
public final class MyModel {
    public private(set) var value: Int

    public init(value: Int = 0) {
        self.value = value
    }

    public func increment() {
        value += 1
    }
}
