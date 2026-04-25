//! IFS / AVS Konami LZSS (Okumura-style).
//!
//! Format: 4 KB window, 3..18 byte match length, 8-codes-per-flag-byte framing.
//! Match token is a big-endian u16: top 12 bits = back-distance, bottom 4 = (length - 3).
//! Distance == 0 is the EOS sentinel. Distances point into a virtual zero-prefilled
//! window before the start of the stream.

const WINDOW: usize = 0x1000;
const MAX_DIST: usize = WINDOW - 1; // 4095, since 0 is the EOS sentinel
const F: usize = 18;                // max match length
const THRESHOLD: usize = 3;         // min match length

const HASH_BITS: u32 = 13;
const HASH_SIZE: usize = 1 << HASH_BITS;
const HASH_MASK: u32 = HASH_SIZE as u32 - 1;
const NIL: u32 = u32::MAX;

#[derive(Debug)]
pub enum DecompressError {
    Truncated,
}

impl std::fmt::Display for DecompressError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DecompressError::Truncated => write!(f, "truncated lz77 stream"),
        }
    }
}

impl std::error::Error for DecompressError {}

pub fn decompress(input: &[u8]) -> Result<Vec<u8>, DecompressError> {
    let mut out: Vec<u8> = Vec::with_capacity(input.len() * 2);
    let mut i = 0usize;

    loop {
        if i >= input.len() {
            return Err(DecompressError::Truncated);
        }
        let flag = input[i];
        i += 1;

        for bit in 0..8 {
            if (flag >> bit) & 1 == 1 {
                if i >= input.len() {
                    return Err(DecompressError::Truncated);
                }
                out.push(input[i]);
                i += 1;
            } else {
                if i + 1 >= input.len() {
                    return Err(DecompressError::Truncated);
                }
                let w = u16::from_be_bytes([input[i], input[i + 1]]);
                i += 2;

                let pos = (w >> 4) as usize;
                let mut len = (w & 0x0F) as usize + THRESHOLD;

                if pos == 0 {
                    return Ok(out);
                }

                // References into the virtual zero-prefilled window before stream start.
                if pos > out.len() {
                    let diff = (pos - out.len()).min(len);
                    out.extend(std::iter::repeat(0u8).take(diff));
                    len -= diff;
                }

                // Self-overlapping copy: each output byte may feed the next.
                let start = out.len() - pos;
                for k in 0..len {
                    let b = out[start + k];
                    out.push(b);
                }
            }
        }
    }
}

/// Hash a 3-byte prefix into the chain table.
#[inline(always)]
fn hash3(a: u8, b: u8, c: u8) -> usize {
    let h = ((a as u32) << 16) | ((b as u32) << 8) | (c as u32);
    let h = h.wrapping_mul(0x1e35a7bd);
    ((h >> (32 - HASH_BITS)) & HASH_MASK) as usize
}

/// Compress a buffer. Output is byte-identical to the reference Python encoder
/// when the matcher decisions agree (greedy longest-match here vs. greedy
/// longest-match there).
pub fn compress(input: &[u8]) -> Vec<u8> {
    // Pre-pend a 4 KB zero window so matches at the start can legitimately
    // reference into the zero-prefilled history that the decoder synthesises.
    let mut buf = vec![0u8; WINDOW];
    buf.extend_from_slice(input);
    let buf_len = buf.len();

    let mut head = vec![NIL; HASH_SIZE];
    let mut prev = vec![NIL; WINDOW];

    // Seed the hash chain with the zero prefix so the encoder can find matches
    // pointing into it. Stop before the input cursor and respect buf_len so we
    // never index past the end on tiny inputs.
    let seed_limit = (WINDOW - 1).min(buf_len.saturating_sub(2));
    for p in 0..seed_limit {
        let h = hash3(buf[p], buf[p + 1], buf[p + 2]);
        prev[p & (WINDOW - 1)] = head[h];
        head[h] = p as u32;
    }

    let mut out: Vec<u8> = Vec::with_capacity(input.len());
    let mut pos = WINDOW;

    while pos < buf_len {
        let mut flag_byte: u8 = 0;
        let mut group: Vec<u8> = Vec::with_capacity(8 * 2);

        for bit in 0..8 {
            if pos >= buf_len {
                // Out of input mid-group: leave the bit as match (0). The
                // decoder will read into our trailing 0x00 0x00 0x00 sentinel
                // and exit on the position == 0 check before reaching this
                // phantom slot.
                continue;
            }

            let (best_len, best_dist) = find_match(&buf, pos, &head, &prev);

            if best_len >= THRESHOLD {
                let dist = best_dist as u16;
                let info: u16 = (dist << 4) | ((best_len - THRESHOLD) as u16);
                group.extend_from_slice(&info.to_be_bytes());

                // Insert hash entries for every position covered by the match,
                // including the start (which we are about to skip past).
                for k in 0..best_len {
                    let p = pos + k;
                    if p + 2 < buf_len {
                        let h = hash3(buf[p], buf[p + 1], buf[p + 2]);
                        prev[p & (WINDOW - 1)] = head[h];
                        head[h] = p as u32;
                    }
                }
                pos += best_len;
            } else {
                group.push(buf[pos]);
                flag_byte |= 1 << bit;

                if pos + 2 < buf_len {
                    let h = hash3(buf[pos], buf[pos + 1], buf[pos + 2]);
                    prev[pos & (WINDOW - 1)] = head[h];
                    head[h] = pos as u32;
                }
                pos += 1;
            }
        }

        out.push(flag_byte);
        out.extend_from_slice(&group);
    }

    // EOS sentinel: flag byte saying "next code is a match", then a 0x0000
    // match token (distance == 0 → decoder returns).
    out.push(0);
    out.push(0);
    out.push(0);
    out
}

#[inline]
fn find_match(buf: &[u8], pos: usize, head: &[u32], prev: &[u32]) -> (usize, usize) {
    let buf_len = buf.len();
    if pos + THRESHOLD > buf_len {
        return (0, 0);
    }

    let max_len = (buf_len - pos).min(F);
    if max_len < THRESHOLD {
        return (0, 0);
    }

    let h = hash3(buf[pos], buf[pos + 1], buf[pos + 2]);
    let mut candidate = head[h];
    let limit = pos.saturating_sub(MAX_DIST);

    let mut best_len = 0usize;
    let mut best_dist = 0usize;

    // Bound on chain depth — at N=4096 chains are short anyway, but cap to keep
    // worst-case behaviour bounded on highly repetitive input.
    let mut chain_remaining: u32 = 4096;

    while candidate != NIL {
        let cand = candidate as usize;
        if cand < limit {
            break;
        }
        chain_remaining -= 1;

        // Quick reject: if the byte at best_len doesn't match, skip.
        if best_len > 0 && buf[cand + best_len] != buf[pos + best_len] {
            // fall through to chain step
        } else {
            // Compare bytes up to max_len.
            let mut len = 0usize;
            while len < max_len && buf[cand + len] == buf[pos + len] {
                len += 1;
            }

            if len > best_len {
                best_len = len;
                best_dist = pos - cand;
                if best_len >= max_len {
                    break;
                }
            }
        }

        if chain_remaining == 0 {
            break;
        }
        candidate = prev[cand & (WINDOW - 1)];
    }

    (best_len, best_dist)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_small() {
        let data = b"hello hello hello world! world world world world".to_vec();
        let comp = compress(&data);
        let decomp = decompress(&comp).unwrap();
        assert_eq!(decomp, data);
    }

    #[test]
    fn roundtrip_empty() {
        let comp = compress(&[]);
        let decomp = decompress(&comp).unwrap();
        assert_eq!(decomp, Vec::<u8>::new());
    }

    #[test]
    fn roundtrip_short() {
        let data = b"abc".to_vec();
        let comp = compress(&data);
        let decomp = decompress(&comp).unwrap();
        assert_eq!(decomp, data);
    }

    #[test]
    fn roundtrip_repetitive() {
        let data = vec![0xAAu8; 10_000];
        let comp = compress(&data);
        let decomp = decompress(&comp).unwrap();
        assert_eq!(decomp, data);
    }

    #[test]
    fn roundtrip_random_ish() {
        // Pseudo-random but reproducible.
        let mut data = vec![0u8; 50_000];
        let mut x: u32 = 0x12345678;
        for b in data.iter_mut() {
            x = x.wrapping_mul(1664525).wrapping_add(1013904223);
            *b = (x >> 16) as u8;
        }
        let comp = compress(&data);
        let decomp = decompress(&comp).unwrap();
        assert_eq!(decomp, data);
    }

    #[test]
    fn known_test_vector() {
        // The decoder fixture from _lz77.py main block.
        let test = [
            0x88, 0x46, 0x23, 0x20, 0x00, 0x20, 0x47, 0x20, 0x41, 0x00, 0x10, 0xa2, 0x47,
            0x01, 0xa0, 0x45, 0x20, 0x44, 0x00, 0x08, 0x45, 0x01, 0x50, 0x79, 0x00, 0xc0,
            0x45, 0x20, 0x05, 0x24, 0x13, 0x88, 0x05, 0xb4, 0x02, 0x4a, 0x44, 0xef, 0x03,
            0x58, 0x02, 0x8c, 0x09, 0x16, 0x01, 0x48, 0x45, 0x00, 0xbe, 0x00, 0x9e, 0x00,
            0x04, 0x01, 0x18, 0x90, 0x00, 0x00,
        ];
        let out = decompress(&test).unwrap();
        // Round-trip through our own encoder to confirm the encoder emits a
        // legal stream (not necessarily byte-identical bits).
        let recomp = compress(&out);
        let redec = decompress(&recomp).unwrap();
        assert_eq!(redec, out);
    }
}
