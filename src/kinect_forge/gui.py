from __future__ import annotations

import json
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np

from kinect_forge.calibration import calibrate_intrinsics, save_intrinsics
from kinect_forge.capture import capture_frames
from kinect_forge.config import CaptureConfig, KinectIntrinsics, ReconstructionConfig
from kinect_forge.measure import measure_mesh
from kinect_forge.presets import reconstruction_preset
from kinect_forge.reconstruct import reconstruct_mesh
from kinect_forge.sensors.freenect_v1 import FreenectV1Sensor, probe_device
from kinect_forge.turntable import get_turntable_preset
from kinect_forge.viewer import view_dataset, view_mesh


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Kinect Forge")
        self._preview_image: Optional[tk.PhotoImage] = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(self.root, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=False)

        self._build_status_tab()
        self._build_capture_tab()
        self._build_reconstruct_tab()
        self._build_measure_tab()
        self._build_view_tab()
        self._build_calibrate_tab()
        self.root.after(500, self._refresh_dataset_state)

    def _log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _dataset_ready(self, root: str) -> bool:
        if not root:
            return False
        return (Path(root) / "metadata.json").is_file()

    def _require_dataset(self, root: str, label: str) -> bool:
        if self._dataset_ready(root):
            return True
        self._log(f"[{label}] error: metadata.json not found in {root}")
        self._log("Run Capture first to create a dataset.")
        return False

    def _require_mesh(self, path: str, label: str) -> bool:
        if not path:
            self._log(f"[{label}] error: mesh path is empty")
            return False
        mesh_path = Path(path)
        if not mesh_path.is_file():
            self._log(f"[{label}] error: mesh file not found: {mesh_path}")
            return False
        if mesh_path.stat().st_size == 0:
            self._log(f"[{label}] error: mesh file is empty: {mesh_path}")
            return False
        return True

    def _run_task(self, label: str, fn: Callable[[], None]) -> None:
        def runner() -> None:
            self._log(f"[{label}] started")
            try:
                fn()
                self._log(f"[{label}] completed")
            except Exception as exc:  # pragma: no cover
                self._log(f"[{label}] error: {exc}")

        threading.Thread(target=runner, daemon=True).start()

    def _build_status_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Status")

        label = ttk.Label(frame, text="Check Kinect v1 backend status")
        label.pack(anchor=tk.W, padx=8, pady=8)
        env_label = ttk.Label(frame, text=f"Python: {sys.executable}")
        env_label.pack(anchor=tk.W, padx=8, pady=2)
        freenect_label = ttk.Label(frame, text="Freenect: checking...")
        freenect_label.pack(anchor=tk.W, padx=8, pady=2)

        try:
            import freenect  # type: ignore

            _ = freenect  # silence unused
            freenect_label.config(text="Freenect: import OK")
        except Exception as exc:  # pragma: no cover
            freenect_label.config(text=f"Freenect: not available ({exc})")

        def check() -> None:
            ok = probe_device()
            if ok:
                self._log("Kinect v1 backend detected and streaming.")
            else:
                self._log(
                    "Kinect v1 backend not detected. Install libfreenect + python3-freenect."
                )

        ttk.Button(frame, text="Check Status", command=lambda: self._run_task("status", check)).pack(
            anchor=tk.W, padx=8, pady=4
        )

    def _build_capture_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Capture")

        self.capture_output = tk.StringVar(value="captures")
        self.capture_frames = tk.IntVar(value=300)
        self.capture_fps = tk.DoubleVar(value=30.0)
        self.capture_warmup = tk.IntVar(value=15)
        self.capture_mode = tk.StringVar(value="standard")
        self.capture_change = tk.DoubleVar(value=0.01)
        self.capture_max_total = tk.IntVar(value=3000)
        self.capture_depth_min = tk.DoubleVar(value=0.3)
        self.capture_depth_max = tk.DoubleVar(value=2.5)
        self.capture_mask = tk.BooleanVar(value=True)
        self.capture_auto_stop = tk.BooleanVar(value=False)
        self.capture_auto_patience = tk.IntVar(value=30)
        self.capture_auto_delta = tk.DoubleVar(value=0.002)
        self.capture_roi = tk.StringVar(value="")
        self.capture_color_mask = tk.BooleanVar(value=False)
        self.capture_hsv_lower = tk.StringVar(value="0,0,0")
        self.capture_hsv_upper = tk.StringVar(value="179,255,255")
        self.capture_turntable_model = tk.StringVar(value="")
        self.capture_turntable_diameter = tk.StringVar(value="")
        self.capture_turntable_rotation = tk.StringVar(value="")
        self.capture_turntable_preset = tk.StringVar(value="")
        self.capture_intrinsics = tk.StringVar(value="")
        self.capture_preview = tk.BooleanVar(value=True)

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=8, pady=8)

        def run_capture() -> None:
            try:
                sensor = FreenectV1Sensor()
            except Exception as exc:  # pragma: no cover
                self._log(f"Capture failed: {exc}")
                self._log("Ensure freenect is installed in this Python environment.")
                return
            config = CaptureConfig(
                frames=self.capture_frames.get(),
                fps=self.capture_fps.get(),
                warmup=self.capture_warmup.get(),
                mode=self.capture_mode.get().lower(),
                change_threshold=self.capture_change.get(),
                max_frames_total=self.capture_max_total.get(),
                depth_min=self.capture_depth_min.get(),
                depth_max=self.capture_depth_max.get(),
                mask_background=self.capture_mask.get(),
                auto_stop=self.capture_auto_stop.get(),
                auto_stop_patience=self.capture_auto_patience.get(),
                auto_stop_delta=self.capture_auto_delta.get(),
                roi_x=0,
                roi_y=0,
                roi_w=0,
                roi_h=0,
                color_mask=self.capture_color_mask.get(),
                hsv_lower=(0, 0, 0),
                hsv_upper=(179, 255, 255),
                turntable_model=self.capture_turntable_model.get() or None,
                turntable_diameter_mm=int(self.capture_turntable_diameter.get())
                if self.capture_turntable_diameter.get()
                else None,
                turntable_rotation_seconds=float(self.capture_turntable_rotation.get())
                if self.capture_turntable_rotation.get()
                else None,
            )
            if self.capture_turntable_preset.get():
                preset = get_turntable_preset(self.capture_turntable_preset.get())
                config = CaptureConfig(
                    **{
                        **config.__dict__,
                        "turntable_model": preset.model,
                        "turntable_diameter_mm": preset.diameter_mm,
                        "turntable_rotation_seconds": preset.rotation_seconds,
                    }
                )
            if self.capture_roi.get():
                roi_parts = [p.strip() for p in self.capture_roi.get().split(",")]
                if len(roi_parts) == 4:
                    config = CaptureConfig(
                        **{
                            **config.__dict__,
                            "roi_x": int(roi_parts[0]),
                            "roi_y": int(roi_parts[1]),
                            "roi_w": int(roi_parts[2]),
                            "roi_h": int(roi_parts[3]),
                        }
                    )
            if self.capture_hsv_lower.get():
                parts = [int(p.strip()) for p in self.capture_hsv_lower.get().split(",")]
                if len(parts) == 3:
                    config = CaptureConfig(**{**config.__dict__, "hsv_lower": tuple(parts)})
            if self.capture_hsv_upper.get():
                parts = [int(p.strip()) for p in self.capture_hsv_upper.get().split(",")]
                if len(parts) == 3:
                    config = CaptureConfig(**{**config.__dict__, "hsv_upper": tuple(parts)})
            intrinsics = None
            if self.capture_intrinsics.get():
                payload = json.loads(Path(self.capture_intrinsics.get()).read_text())
                intrinsics = KinectIntrinsics.from_dict(payload)

            def preview_cb(color: np.ndarray, depth: np.ndarray) -> None:
                if not self.capture_preview.get():
                    return
                ppm = self._to_ppm_bytes(color)
                if not ppm:
                    return
                self.root.after(0, self._update_preview, ppm)

            capture_frames(
                sensor,
                Path(self.capture_output.get()),
                config,
                intrinsics=intrinsics,
                preview_cb=preview_cb,
            )
            self._log("Capture dataset ready.")

        self.capture_button = ttk.Button(
            action_frame,
            text="● Start Capture",
            command=lambda: self._run_task("capture", run_capture),
        )
        self.capture_button.pack(anchor=tk.W)

        self._path_row(frame, "Output", self.capture_output, 1, is_dir=True)
        self._entry_row(frame, "Frames", self.capture_frames, 2)
        self._entry_row(frame, "FPS", self.capture_fps, 3)
        self._entry_row(frame, "Warmup", self.capture_warmup, 4)
        self._entry_row(frame, "Mode", self.capture_mode, 5)
        self._entry_row(frame, "Change Threshold (m)", self.capture_change, 6)
        self._entry_row(frame, "Max Frames Total", self.capture_max_total, 7)
        self._entry_row(frame, "Depth Min (m)", self.capture_depth_min, 8)
        self._entry_row(frame, "Depth Max (m)", self.capture_depth_max, 9)

        mask_frame = ttk.Frame(frame)
        mask_frame.grid(row=10, column=0, columnspan=3, sticky=tk.W, padx=8, pady=4)
        ttk.Checkbutton(mask_frame, text="Mask Background", variable=self.capture_mask).pack(
            anchor=tk.W
        )
        ttk.Checkbutton(mask_frame, text="Auto-stop", variable=self.capture_auto_stop).pack(
            anchor=tk.W
        )

        self._entry_row(frame, "Auto-stop Patience", self.capture_auto_patience, 11)
        self._entry_row(frame, "Auto-stop Delta (m)", self.capture_auto_delta, 12)
        self._entry_row(frame, "ROI x,y,w,h", self.capture_roi, 13)
        self._entry_row(frame, "HSV Lower h,s,v", self.capture_hsv_lower, 14)
        self._entry_row(frame, "HSV Upper h,s,v", self.capture_hsv_upper, 15)

        color_frame = ttk.Frame(frame)
        color_frame.grid(row=16, column=0, columnspan=3, sticky=tk.W, padx=8, pady=4)
        ttk.Checkbutton(
            color_frame, text="Enable Color Mask", variable=self.capture_color_mask
        ).pack(anchor=tk.W)

        self._entry_row(frame, "Turntable Preset (vxb-8)", self.capture_turntable_preset, 17)
        self._entry_row(frame, "Turntable Model", self.capture_turntable_model, 18)
        self._entry_row(frame, "Turntable Diameter (mm)", self.capture_turntable_diameter, 19)
        self._entry_row(frame, "Rotation Period (s)", self.capture_turntable_rotation, 20)

        self._path_row(frame, "Intrinsics JSON", self.capture_intrinsics, 21, is_dir=False)

        preview_frame = ttk.Frame(frame)
        preview_frame.grid(row=22, column=0, columnspan=3, sticky=tk.W, padx=8, pady=4)
        ttk.Checkbutton(
            preview_frame, text="Live Preview (Kinect)", variable=self.capture_preview
        ).pack(anchor=tk.W)
        self.capture_preview_label = ttk.Label(preview_frame)
        self.capture_preview_label.pack(anchor=tk.W, pady=4)

    @staticmethod
    def _to_ppm_bytes(color: np.ndarray, max_width: int = 480) -> bytes:
        if color.ndim != 3 or color.shape[2] != 3:
            return b""
        height, width, _ = color.shape
        step = 1
        if width > max_width:
            step = max(1, width // max_width)
        if step > 1:
            color = color[::step, ::step]
            height, width, _ = color.shape
        color = np.ascontiguousarray(color)
        header = f"P6 {width} {height} 255\n".encode("ascii")
        return header + color.tobytes()

    def _update_preview(self, ppm: bytes) -> None:
        if not self.capture_preview.get():
            return
        image = tk.PhotoImage(data=ppm)
        self._preview_image = image
        self.capture_preview_label.configure(image=image)

    def _refresh_dataset_state(self) -> None:
        capture_root = self.capture_output.get()
        dataset_ready = self._dataset_ready(capture_root)
        if dataset_ready:
            if not self.view_dataset_path.get():
                self.view_dataset_path.set(capture_root)
            if not self.recon_input.get():
                self.recon_input.set(capture_root)
            if self.recon_output.get() in {"", "model.ply"}:
                self.recon_output.set(str(Path(capture_root) / "model.ply"))
            self.view_button.state(["!disabled"])
            self.recon_button.state(["!disabled"])
        else:
            self.view_button.state(["disabled"])
            self.recon_button.state(["disabled"])
        self.root.after(1000, self._refresh_dataset_state)

    def _build_reconstruct_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Reconstruct")

        self.recon_input = tk.StringVar(value="")
        self.recon_output = tk.StringVar(value="model.ply")
        self.recon_preset = tk.StringVar(value="small")
        self.recon_voxel = tk.DoubleVar(value=0.003)
        self.recon_sdf = tk.DoubleVar(value=0.03)
        self.recon_depth_scale = tk.DoubleVar(value=1000.0)
        self.recon_depth_trunc = tk.DoubleVar(value=2.0)
        self.recon_keyframe = tk.DoubleVar(value=0.003)
        self.recon_icp = tk.BooleanVar(value=True)
        self.recon_icp_distance = tk.DoubleVar(value=0.015)
        self.recon_icp_voxel = tk.DoubleVar(value=0.008)
        self.recon_icp_iter = tk.IntVar(value=40)
        self.recon_smooth = tk.IntVar(value=5)
        self.recon_fill = tk.DoubleVar(value=0.008)

        self._path_row(frame, "Input Dataset", self.recon_input, 0, is_dir=True)
        self._path_row(frame, "Output Mesh", self.recon_output, 1, is_dir=False, is_save=True)
        self._entry_row(frame, "Preset", self.recon_preset, 2)
        self._entry_row(frame, "Voxel Length", self.recon_voxel, 3)
        self._entry_row(frame, "SDF Trunc", self.recon_sdf, 4)
        self._entry_row(frame, "Depth Scale", self.recon_depth_scale, 5)
        self._entry_row(frame, "Depth Trunc", self.recon_depth_trunc, 6)
        self._entry_row(frame, "Keyframe Threshold", self.recon_keyframe, 7)

        icp_frame = ttk.Frame(frame)
        icp_frame.grid(row=8, column=0, columnspan=3, sticky=tk.W, padx=8, pady=4)
        ttk.Checkbutton(icp_frame, text="ICP Refine", variable=self.recon_icp).pack(anchor=tk.W)

        self._entry_row(frame, "ICP Distance", self.recon_icp_distance, 9)
        self._entry_row(frame, "ICP Voxel", self.recon_icp_voxel, 10)
        self._entry_row(frame, "ICP Iterations", self.recon_icp_iter, 11)
        self._entry_row(frame, "Smooth Iterations", self.recon_smooth, 12)
        self._entry_row(frame, "Fill Hole Radius", self.recon_fill, 13)

        def apply_preset() -> None:
            preset_cfg = reconstruction_preset(self.recon_preset.get())
            self.recon_voxel.set(preset_cfg.voxel_length)
            self.recon_sdf.set(preset_cfg.sdf_trunc)
            self.recon_depth_scale.set(preset_cfg.depth_scale)
            self.recon_depth_trunc.set(preset_cfg.depth_trunc)
            self.recon_keyframe.set(preset_cfg.keyframe_threshold)
            self.recon_icp.set(preset_cfg.icp_refine)
            self.recon_icp_distance.set(preset_cfg.icp_distance)
            self.recon_icp_voxel.set(preset_cfg.icp_voxel)
            self.recon_icp_iter.set(preset_cfg.icp_iterations)
            self.recon_smooth.set(preset_cfg.smooth_iterations)
            self.recon_fill.set(preset_cfg.fill_hole_radius)

        def run_reconstruct() -> None:
            if not self._require_dataset(self.recon_input.get(), "reconstruct"):
                return
            output_text = self.recon_output.get().strip()
            if not output_text:
                self._log("[reconstruct] error: output mesh path is empty")
                return
            output_path = Path(output_text)
            if output_path.exists() and output_path.is_dir():
                output_path = output_path / "model.ply"
                self.recon_output.set(str(output_path))
            if output_path.suffix == "":
                output_path = output_path.with_suffix(".ply")
                self.recon_output.set(str(output_path))
            config = ReconstructionConfig(
                voxel_length=self.recon_voxel.get(),
                sdf_trunc=self.recon_sdf.get(),
                depth_scale=self.recon_depth_scale.get(),
                depth_trunc=self.recon_depth_trunc.get(),
                keyframe_threshold=self.recon_keyframe.get(),
                icp_refine=self.recon_icp.get(),
                icp_distance=self.recon_icp_distance.get(),
                icp_voxel=self.recon_icp_voxel.get(),
                icp_iterations=self.recon_icp_iter.get(),
                smooth_iterations=self.recon_smooth.get(),
                fill_hole_radius=self.recon_fill.get(),
                preset=self.recon_preset.get(),
            )
            reconstruct_mesh(Path(self.recon_input.get()), output_path, config)

        self.recon_button = ttk.Button(
            frame,
            text="Reconstruct",
            command=lambda: self._run_task("reconstruct", run_reconstruct),
        )
        self.recon_button.grid(row=14, column=0, padx=8, pady=8, sticky=tk.W)
        self.recon_button.state(["disabled"])

        ttk.Button(frame, text="Apply Preset", command=apply_preset).grid(
            row=14, column=1, padx=8, pady=8, sticky=tk.W
        )

    def _build_measure_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Measure")

        self.measure_mesh_path = tk.StringVar(value="")
        self._path_row(frame, "Mesh", self.measure_mesh_path, 0, is_dir=False)

        def run_measure() -> None:
            if not self._require_mesh(self.measure_mesh_path.get(), "measure"):
                return
            measurements = measure_mesh(Path(self.measure_mesh_path.get()))
            self._log(
                "Axis-aligned (m): "
                f"{measurements.axis_aligned[0]:.4f}, "
                f"{measurements.axis_aligned[1]:.4f}, "
                f"{measurements.axis_aligned[2]:.4f}"
            )
            self._log(
                "Oriented (m): "
                f"{measurements.oriented[0]:.4f}, "
                f"{measurements.oriented[1]:.4f}, "
                f"{measurements.oriented[2]:.4f}"
            )
            if measurements.volume is not None:
                self._log(f"Volume (m^3): {measurements.volume:.6f}")

        ttk.Button(frame, text="Measure", command=lambda: self._run_task("measure", run_measure)).grid(
            row=1, column=0, padx=8, pady=8, sticky=tk.W
        )

    def _build_view_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="View")

        self.view_mesh_path = tk.StringVar(value="")
        self.view_dataset_path = tk.StringVar(value="")
        self.view_every = tk.IntVar(value=10)

        self._path_row(frame, "Mesh", self.view_mesh_path, 0, is_dir=False)
        self._path_row(frame, "Dataset", self.view_dataset_path, 1, is_dir=True)
        self._entry_row(frame, "Every Nth Frame", self.view_every, 2)

        def run_view() -> None:
            if self.view_dataset_path.get():
                if not self._require_dataset(self.view_dataset_path.get(), "view"):
                    return
                view_dataset(Path(self.view_dataset_path.get()), every=self.view_every.get())
            if self.view_mesh_path.get():
                view_mesh(Path(self.view_mesh_path.get()))

        self.view_button = ttk.Button(
            frame, text="Open Viewer", command=lambda: self._run_task("view", run_view)
        )
        self.view_button.grid(row=3, column=0, padx=8, pady=8, sticky=tk.W)
        self.view_button.state(["disabled"])

    def _build_calibrate_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Calibrate")

        self.calib_images = tk.StringVar(value="")
        self.calib_rows = tk.IntVar(value=7)
        self.calib_cols = tk.IntVar(value=9)
        self.calib_square = tk.DoubleVar(value=0.025)
        self.calib_output = tk.StringVar(value="intrinsics.json")

        self._path_row(frame, "Images Glob", self.calib_images, 0, is_dir=False)
        self._entry_row(frame, "Rows", self.calib_rows, 1)
        self._entry_row(frame, "Cols", self.calib_cols, 2)
        self._entry_row(frame, "Square Size (m)", self.calib_square, 3)
        self._path_row(frame, "Output JSON", self.calib_output, 4, is_dir=False, is_save=True)

        def run_calibrate() -> None:
            paths = [Path(p) for p in Path().glob(self.calib_images.get())]
            intrinsics = calibrate_intrinsics(
                paths, (self.calib_cols.get(), self.calib_rows.get()), self.calib_square.get()
            )
            save_intrinsics(Path(self.calib_output.get()), intrinsics)
            self._log(f"Intrinsics saved to {self.calib_output.get()}")
            self._log(json.dumps(asdict(intrinsics), indent=2))

        ttk.Button(
            frame, text="Calibrate", command=lambda: self._run_task("calibrate", run_calibrate)
        ).grid(row=5, column=0, padx=8, pady=8, sticky=tk.W)

    def _entry_row(self, frame: ttk.Frame, label: str, var: tk.Variable, row: int) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(frame, textvariable=var, width=30).grid(
            row=row, column=1, sticky=tk.W, padx=8, pady=4
        )

    def _path_row(
        self,
        frame: ttk.Frame,
        label: str,
        var: tk.Variable,
        row: int,
        is_dir: bool,
        is_save: bool = False,
    ) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(frame, textvariable=var, width=30).grid(
            row=row, column=1, sticky=tk.W, padx=8, pady=4
        )

        def browse() -> None:
            if is_dir:
                path = filedialog.askdirectory()
            elif is_save:
                path = filedialog.asksaveasfilename()
            else:
                path = filedialog.askopenfilename()
            if path:
                var.set(path)

        ttk.Button(frame, text="Browse", command=browse).grid(
            row=row, column=2, sticky=tk.W, padx=8, pady=4
        )


def launch_gui() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
