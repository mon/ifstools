use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

mod lz77;

#[pyfunction]
#[pyo3(name = "decompress")]
fn py_decompress<'py>(py: Python<'py>, data: Vec<u8>) -> PyResult<Bound<'py, PyBytes>> {
    let out = py
        .detach(|| lz77::decompress(&data))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &out))
}

#[pyfunction]
#[pyo3(name = "compress", signature = (data, progress=false))]
fn py_compress<'py>(
    py: Python<'py>,
    data: Vec<u8>,
    progress: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let _ = progress; // Pure-Python signature parity; matcher itself is silent.
    let out = py.detach(|| lz77::compress(&data));
    Ok(PyBytes::new(py, &out))
}

#[pymodule]
#[pyo3(name = "_lz77_native")]
fn _lz77_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(py_compress, m)?)?;
    Ok(())
}
