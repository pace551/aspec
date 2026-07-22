//! Thin binary over the lib (STK-RUST-07); anyhow chains errors for humans
//! (STK-RUST-03).

fn main() -> anyhow::Result<()> {
    println!("{{PROJECT_NAME}} {}", {{PROJECT_NAME}}::VERSION);
    Ok(())
}
