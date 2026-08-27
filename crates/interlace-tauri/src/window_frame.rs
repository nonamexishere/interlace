//! Persist the main window frame (x/y + width/height) next to other App Support files.

use std::fs;
use std::path::PathBuf;

use interlace_core::session::config_dir;
use serde::{Deserialize, Serialize};
use tauri::{Monitor, PhysicalPosition, PhysicalSize, Runtime, WebviewWindow, Window};

const FRAME_FILE: &str = "window-frame.json";

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
struct WindowFrame {
    x: i32,
    y: i32,
    width: u32,
    height: u32,
}

fn frame_path() -> PathBuf {
    config_dir().join(FRAME_FILE)
}

fn read_window_frame() -> Option<WindowFrame> {
    let text = fs::read_to_string(frame_path()).ok()?;
    let frame: WindowFrame = serde_json::from_str(&text).ok()?;
    if frame.width == 0 || frame.height == 0 {
        return None;
    }
    Some(frame)
}

fn write_window_frame(frame: WindowFrame) {
    if frame.width == 0 || frame.height == 0 {
        return;
    }
    let dir = config_dir();
    if fs::create_dir_all(&dir).is_err() {
        return;
    }
    if let Ok(body) = serde_json::to_string(&frame) {
        let _ = fs::write(dir.join(FRAME_FILE), body);
    }
}

fn has_intersection(frame: WindowFrame, ax: i32, ay: i32, aw: u32, ah: u32) -> bool {
    if aw == 0 || ah == 0 {
        return false;
    }
    let x2 = frame.x as i64 + frame.width as i64;
    let y2 = frame.y as i64 + frame.height as i64;
    let ax2 = ax as i64 + aw as i64;
    let ay2 = ay as i64 + ah as i64;
    (frame.x as i64) < ax2 && (frame.y as i64) < ay2 && (ax as i64) < x2 && (ay as i64) < y2
}

fn translate(pos: i32, size: u32, area_pos: i32, area_size: u32) -> i32 {
    let pos = pos as i64;
    let size = size as i64;
    let area_pos = area_pos as i64;
    let area_end = area_pos + area_size as i64;
    let out = if pos + size <= area_pos {
        area_pos
    } else if pos >= area_end {
        area_end - size
    } else {
        pos
    };
    out.clamp(i32::MIN as i64, i32::MAX as i64) as i32
}

fn clamp_window_frame(frame: WindowFrame, monitors: &[Monitor]) -> WindowFrame {
    for m in monitors {
        let area = m.work_area();
        if has_intersection(
            frame,
            area.position.x,
            area.position.y,
            area.size.width,
            area.size.height,
        ) {
            return frame;
        }
    }
    let Some(m) = monitors.first() else {
        return frame;
    };
    let area = m.work_area();
    let mut x = frame.x;
    let mut y = frame.y;
    x = translate(x, frame.width, area.position.x, area.size.width);
    y = translate(y, frame.height, area.position.y, area.size.height);
    WindowFrame {
        x,
        y,
        width: frame.width,
        height: frame.height,
    }
}

pub fn restore_window_frame<R: Runtime>(window: &WebviewWindow<R>) {
    let Some(saved) = read_window_frame() else {
        return;
    };
    let monitors = window.available_monitors().unwrap_or_default();
    let frame = clamp_window_frame(saved, &monitors);
    let _ = window.set_size(PhysicalSize::new(frame.width, frame.height));
    let _ = window.set_position(PhysicalPosition::new(frame.x, frame.y));
}

pub fn save_window_frame<R: Runtime>(window: &Window<R>) {
    if window.label() != "main" {
        return;
    }
    let Ok(size) = window.inner_size() else {
        return;
    };
    let Ok(pos) = window.outer_position() else {
        return;
    };
    if size.width == 0 || size.height == 0 {
        return;
    }
    write_window_frame(WindowFrame {
        x: pos.x,
        y: pos.y,
        width: size.width,
        height: size.height,
    });
}
