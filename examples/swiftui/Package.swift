// swift-tools-version: 6.0
// CounterKit — STK-SWIFT worked example: SPM library, @Observable model, Swift Testing.
// Dependencies via SPM only (STK-SWIFT-04); none needed here.
import PackageDescription

let package = Package(
    name: "CounterKit",
    platforms: [.macOS(.v14), .iOS(.v17)],  // current targets: Observation available (STK-SWIFT-02)
    products: [
        .library(name: "CounterKit", targets: ["CounterKit"])
    ],
    targets: [
        .target(name: "CounterKit"),
        .testTarget(name: "CounterKitTests", dependencies: ["CounterKit"]),
    ]
)
