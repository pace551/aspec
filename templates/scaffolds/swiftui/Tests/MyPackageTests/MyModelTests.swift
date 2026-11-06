// Swift Testing (STK-SWIFT-06): @Test + #expect, run via swift test / stk-swift-verify.sh.
@testable import MyPackage
import Testing

@Test func incrementRaisesValue() {
    let model = MyModel()
    model.increment()
    #expect(model.value == 1)
}
