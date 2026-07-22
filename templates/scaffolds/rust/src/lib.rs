//! {{PROJECT_NAME}} — {{ONE_LINE_DESCRIPTION}}
//!
//! Logic lives here with typed errors; `main.rs` stays a thin anyhow shim
//! (STK-RUST-03, STK-RUST-07).

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Placeholder error type — extend per feature, keep variants matchable.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum Error {
    #[error("not yet implemented")]
    Unimplemented,
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)] // test-code carve-out (STK-RUST-03)

    use super::*;

    // Replace with real tests; Constitution C3 requires test-first core logic.
    #[test]
    fn version_is_nonempty() {
        assert!(!VERSION.is_empty());
    }
}
