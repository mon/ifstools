use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

mod dxt;
mod lz77;
mod png_enc;

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

#[pyfunction]
#[pyo3(name = "encode_png", signature = (width, height, pixels, color="rgba"))]
fn py_encode_png<'py>(
    py: Python<'py>,
    width: u32,
    height: u32,
    pixels: Vec<u8>,
    color: &str,
) -> PyResult<Bound<'py, PyBytes>> {
    let out = py
        .detach(|| png_enc::encode(width, height, &pixels, color))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &out))
}

#[pyfunction]
#[pyo3(name = "decode_dxt")]
fn py_decode_dxt<'py>(
    py: Python<'py>,
    data: Vec<u8>,
    width: usize,
    height: usize,
    format: &str,
) -> PyResult<Bound<'py, PyBytes>> {
    let out = py
        .detach(|| dxt::decode(&data, width, height, format))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &out))
}

#[pymodule]
#[pyo3(name = "_native")]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(py_compress, m)?)?;
    m.add_function(wrap_pyfunction!(py_encode_png, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_dxt, m)?)?;
    Ok(())
}
