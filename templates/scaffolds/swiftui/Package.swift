// swift-tools-version: 6.0
// STK-SWIFT scaffold — /bootstrap-repo renames MyPackage to the project name.
// Dependencies via SPM only (STK-SWIFT-04); commit Package.resolved once deps exist.
import PackageDescription

let package = Package(
    name: "MyPackage",
    platforms: [.macOS(.v14), .iOS(.v17)],  // current targets: Observation available (STK-SWIFT-02)
    products: [
        .library(name: "MyPackage", targets: ["MyPackage"])
    ],
    targets: [
        .target(name: "MyPackage"),
        .testTarget(name: "MyPackageTests", dependencies: ["MyPackage"]),
    ]
)
