// Swift Testing (STK-SWIFT-06): @Test + #expect, run via swift test /
// checks/stk-swift-verify.sh. Model logic tested with no UI (STK-SWIFT-05).
import Testing

@testable import CounterKit

@Test func incrementMovesByStep() {
    let model = CounterModel(step: 5)
    model.increment()
    #expect(model.count == 5)
}

@Test func incrementStopsAtUpperBound() {
    let model = CounterModel(count: 9, step: 2, range: 0...10)
    model.increment()
    #expect(model.count == 9)  // 11 would exceed the range; guarded, not clamped
    #expect(!model.canIncrement)
}

@Test func decrementStopsAtLowerBound() {
    let model = CounterModel(count: 0)
    model.decrement()
    #expect(model.count == 0)
    #expect(!model.canDecrement)
}

@Test func resetReturnsToLowerBound() {
    let model = CounterModel(count: 7, range: 2...20)
    model.reset()
    #expect(model.count == 2)
}

@Test func outOfRangeInitialCountFallsBackToLowerBound() {
    let model = CounterModel(count: 999, range: 0...10)
    #expect(model.count == 0)
}
