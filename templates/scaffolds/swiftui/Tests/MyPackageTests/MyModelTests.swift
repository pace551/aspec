// Swift Testing (STK-SWIFT-06): @Test + #expect, run via swift test / stk-swift-verify.sh.
import Testing

@testable import MyPackage

@Test func incrementRaisesValue() {
    let model = MyModel()
    model.increment()
    #expect(model.value == 1)
}
