//! Binary half of the STK-RUST error split: thin over the lib, anyhow for
//! human-readable failure chains (STK-RUST-03, STK-RUST-07).
//!
//! Usage: `rpn 3 4 + 2 '*'` (tokens as args; quote `*` from the shell).

use anyhow::Context;

fn main() -> anyhow::Result<()> {
    let expr = std::env::args().skip(1).collect::<Vec<_>>().join(" ");
    let value = rpn::eval(&expr).with_context(|| format!("evaluating {expr:?}"))?;
    println!("{value}");
    Ok(())
}
