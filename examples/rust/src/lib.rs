//! RPN (reverse polish notation) evaluation.
//!
//! Library half of the STK-RUST error split: every failure is a matchable
//! [`RpnError`] variant via `thiserror`; the binary (`main.rs`) wraps with anyhow.
//! No `unwrap()`/`expect()` — the Cargo `[lints]` table denies them (STK-RUST-03).

use thiserror::Error;

/// Everything that can go wrong evaluating an expression.
#[derive(Debug, Error, PartialEq)]
pub enum RpnError {
    #[error("empty expression")]
    EmptyExpression,
    #[error("unknown token {0:?}")]
    UnknownToken(String),
    #[error("operator {op:?} needs two operands, stack has {stack_len}")]
    StackUnderflow { op: String, stack_len: usize },
    #[error("division by zero")]
    DivideByZero,
    #[error("expression leaves {0} values on the stack (expected 1)")]
    TrailingOperands(usize),
}

/// Evaluate a whitespace-separated RPN expression, e.g. `"3 4 + 2 *"` → `14.0`.
pub fn eval(expr: &str) -> Result<f64, RpnError> {
    let mut stack: Vec<f64> = Vec::new();
    let mut saw_token = false;

    for token in expr.split_whitespace() {
        saw_token = true;
        match token {
            "+" | "-" | "*" | "/" => {
                let len = stack.len();
                let (Some(rhs), Some(lhs)) = (stack.pop(), stack.pop()) else {
                    return Err(RpnError::StackUnderflow {
                        op: token.to_string(),
                        stack_len: len,
                    });
                };
                let value = match token {
                    "+" => lhs + rhs,
                    "-" => lhs - rhs,
                    "*" => lhs * rhs,
                    _ => {
                        if rhs == 0.0 {
                            return Err(RpnError::DivideByZero);
                        }
                        lhs / rhs
                    }
                };
                stack.push(value);
            }
            number => {
                let value: f64 = number
                    .parse()
                    .map_err(|_| RpnError::UnknownToken(number.to_string()))?;
                stack.push(value);
            }
        }
    }

    if !saw_token {
        return Err(RpnError::EmptyExpression);
    }
    match stack.pop() {
        Some(value) if stack.is_empty() => Ok(value),
        Some(_) => Err(RpnError::TrailingOperands(stack.len() + 1)),
        // INVARIANT: unreachable — saw_token guarantees at least one push or an
        // earlier error return; kept as a typed error rather than a panic anyway.
        None => Err(RpnError::EmptyExpression),
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)] // test-code carve-out (STK-RUST-03)

    use super::*;

    #[test]
    fn evaluates_a_single_number() {
        assert_eq!(eval("42"), Ok(42.0));
    }

    #[test]
    fn evaluates_composed_arithmetic() {
        // (3 + 4) * 2 - 1
        assert_eq!(eval("3 4 + 2 * 1 -"), Ok(13.0));
        assert_eq!(eval("10 4 -"), Ok(6.0));
        assert_eq!(eval("1 2 /"), Ok(0.5));
    }

    #[test]
    fn empty_expression_is_an_error() {
        assert_eq!(eval("   "), Err(RpnError::EmptyExpression));
    }

    #[test]
    fn unknown_token_is_reported_verbatim() {
        assert_eq!(eval("1 2 %"), Err(RpnError::UnknownToken("%".to_string())));
    }

    #[test]
    fn underflow_reports_operator_and_depth() {
        assert_eq!(
            eval("5 +"),
            Err(RpnError::StackUnderflow {
                op: "+".to_string(),
                stack_len: 1
            })
        );
    }

    #[test]
    fn division_by_zero_is_typed() {
        assert_eq!(eval("1 0 /"), Err(RpnError::DivideByZero));
    }

    #[test]
    fn leftover_operands_are_an_error() {
        assert_eq!(eval("1 2 3 +"), Err(RpnError::TrailingOperands(2)));
    }

    #[test]
    fn callers_can_match_on_variants() {
        // The point of thiserror in a lib: errors are data, not strings.
        let err = eval("1 0 /").unwrap_err();
        assert!(matches!(err, RpnError::DivideByZero));
        assert_eq!(err.to_string(), "division by zero");
    }
}
