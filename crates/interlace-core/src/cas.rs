//! Content-addressed blob store. Implementation lands in PR5.

use crate::model::CoreError;

pub fn cas_put(_bytes: &[u8], _mime_hint: Option<&str>) -> Result<String, CoreError> {
    unimplemented!("CAS lands in PR5")
}

pub fn cas_get(_hash: &str) -> Result<Vec<u8>, CoreError> {
    unimplemented!("CAS lands in PR5")
}
