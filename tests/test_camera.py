"""Stage 4 tests for the camera backend and control contract layer."""

from __future__ import annotations

import ctypes
import inspect
import unittest
from pathlib import Path
from unittest import mock

from webcam_micro.camera import (
    _LIBUVC_GET_CUR,
    _LIBUVC_GET_DEF,
    _LIBUVC_GET_MAX,
    _LIBUVC_GET_MIN,
    _LIBUVC_GET_RES,
    AvFoundationCameraControlBackend,
    BackendPlan,
    CameraBackend,
    CameraControl,
    CameraControlApplyError,
    CameraControlBackend,
    CameraControlChoice,
    CameraControlError,
    CameraDescriptor,
    CameraOpenError,
    CameraOutputError,
    CameraSession,
    FfmpegCameraBackend,
    FfmpegCameraSession,
    LibUVCControlBackend,
    LinuxV4L2CameraControlBackend,
    MissingCameraDependencyError,
    NullCameraBackend,
    NullCameraControlBackend,
    NullCameraSession,
    PreviewFrame,
    QtCameraBackend,
    QtCameraControlBackend,
    QtCameraSession,
    RecordingCropPlan,
    _build_control_backend,
    _configure_libuvc_library,
    _preferred_recording_output_suffix,
    _qt_recording_output_path_for_path,
    _request_macos_camera_permission,
    _request_qt_camera_permission,
    _SelectedCameraControlBackend,
    _V4L2ControlRecord,
    build_backend_plan,
    build_recording_file_filter,
    pack_preview_rgb_rows,
    request_camera_permission,
)
from webcam_micro.error_reporting import WebcamMicroError


def _identity_completion_handler(handler: object) -> object:
    """Return the test handler unchanged."""

    return handler


def _invoke_completion(completion: object) -> None:
    """Invoke a Rubicon block or plain callback used by the test doubles."""

    if completion is None:
        return
    callback = getattr(completion, "func", completion)
    callback(None)


class CameraContractTest(unittest.TestCase):
    """Verify the preview-backend contract and documented backend plan."""

    def test_backend_plan_names_the_active_preview_target(self) -> None:
        """Assert the backend plan captures the Qt preview target."""

        plan = build_backend_plan()

        self.assertIsInstance(plan, BackendPlan)
        self.assertEqual("QtCameraBackend", plan.active_backend)
        self.assertIn("Qt Multimedia", plan.first_device_backend_target)
        self.assertIn(
            "one selected native device-control backend",
            plan.first_device_backend_target,
        )
        self.assertTrue(any("newest frame" in note for note in plan.notes))
        self.assertTrue(any("Qt Multimedia" in note for note in plan.notes))
        self.assertTrue(
            any(
                "one native device-control backend" in note
                for note in plan.notes
            )
        )

    def test_camera_contract_symbols_stay_explicit(self) -> None:
        """Assert the backend contract symbols stay public and named."""

        self.assertEqual("BackendPlan", BackendPlan.__name__)
        self.assertEqual(
            "AvFoundationCameraControlBackend",
            AvFoundationCameraControlBackend.__name__,
        )
        self.assertEqual("CameraBackend", CameraBackend.__name__)
        self.assertEqual(
            "CameraControlBackend",
            CameraControlBackend.__name__,
        )
        self.assertEqual("CameraControl", CameraControl.__name__)
        self.assertEqual("CameraControlChoice", CameraControlChoice.__name__)
        self.assertEqual("CameraDescriptor", CameraDescriptor.__name__)
        self.assertEqual("CameraControlError", CameraControlError.__name__)
        self.assertTrue(issubclass(CameraControlError, WebcamMicroError))
        self.assertEqual("CameraOutputError", CameraOutputError.__name__)
        self.assertTrue(issubclass(CameraOutputError, WebcamMicroError))
        self.assertEqual("CameraOpenError", CameraOpenError.__name__)
        self.assertEqual("CameraSession", CameraSession.__name__)
        self.assertEqual(
            "CameraControlApplyError",
            CameraControlApplyError.__name__,
        )
        self.assertEqual(
            "MissingCameraDependencyError",
            MissingCameraDependencyError.__name__,
        )
        self.assertTrue(
            issubclass(MissingCameraDependencyError, WebcamMicroError)
        )
        configuration_completion_source = inspect.getsource(
            AvFoundationCameraControlBackend._configuration_completion
        )
        self.assertIn("def release", configuration_completion_source)
        self.assertEqual("QtCameraBackend", QtCameraBackend.__name__)
        self.assertEqual("QtCameraSession", QtCameraSession.__name__)
        self.assertEqual("FfmpegCameraBackend", FfmpegCameraBackend.__name__)
        self.assertEqual("FfmpegCameraSession", FfmpegCameraSession.__name__)
        self.assertEqual("LibUVCControlBackend", LibUVCControlBackend.__name__)
        self.assertEqual("NullCameraBackend", NullCameraBackend.__name__)
        self.assertEqual(
            "NullCameraControlBackend",
            NullCameraControlBackend.__name__,
        )
        self.assertEqual("NullCameraSession", NullCameraSession.__name__)
        self.assertEqual("PreviewFrame", PreviewFrame.__name__)
        self.assertEqual("RecordingCropPlan", RecordingCropPlan.__name__)
        self.assertEqual(
            "QtCameraControlBackend",
            QtCameraControlBackend.__name__,
        )
        self.assertEqual(
            "LinuxV4L2CameraControlBackend",
            LinuxV4L2CameraControlBackend.__name__,
        )

        avfoundation_backend = AvFoundationCameraControlBackend()
        self.assertIsInstance(avfoundation_backend.available, bool)

    def test_configure_libuvc_library_binds_exported_symbols(self) -> None:
        """Assert the libuvc binder installs ctypes signatures."""

        class FakeFunction:
            """Track the signatures the binder installs."""

            def __init__(self) -> None:
                """Initialize signature placeholders."""

                self.restype: object | None = None
                self.argtypes: object | None = None

        class FakeLibrary:
            """Expose the small libuvc surface used by the binder."""

            uvc_init = FakeFunction()
            uvc_strerror = FakeFunction()

        _configure_libuvc_library(FakeLibrary)

        self.assertEqual(ctypes.c_int, FakeLibrary.uvc_init.restype)
        self.assertEqual(
            [ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p],
            FakeLibrary.uvc_init.argtypes,
        )
        self.assertEqual(ctypes.c_char_p, FakeLibrary.uvc_strerror.restype)
        self.assertEqual(
            [ctypes.c_int],
            FakeLibrary.uvc_strerror.argtypes,
        )
        configure_source = inspect.getsource(_configure_libuvc_library)
        self.assertIn("def bind", configure_source)

    def test_libuvc_numeric_record_scales_values(self) -> None:
        """Assert libuvc numeric records convert raw values into units."""

        class FakeLibrary:
            """Expose the minimal getter used by the numeric helper."""

            def uvc_get_test(
                self,
                handle: object,
                value_ptr: object,
                req_code: int,
            ) -> int:
                """Store deterministic raw values for each request."""

                values = {
                    _LIBUVC_GET_CUR: 12,
                    _LIBUVC_GET_DEF: 10,
                    _LIBUVC_GET_MIN: 5,
                    _LIBUVC_GET_MAX: 20,
                    _LIBUVC_GET_RES: 2,
                }
                raw_value_ptr = ctypes.cast(
                    value_ptr,
                    ctypes.POINTER(ctypes.c_uint16),
                )
                raw_value_ptr[0] = values[req_code]
                return 0

        backend = object.__new__(LibUVCControlBackend)
        backend._lib = FakeLibrary()
        backend._context = None
        backend._handle = object()

        record = backend._numeric_record(
            control_id="brightness",
            label="Brightness",
            getter_name="uvc_get_test",
            setter_name="uvc_set_test",
            unit_id=1,
            selector=2,
            value_type=ctypes.c_uint16,
            scale=0.1,
            details="Scaled numeric record.",
        )

        self.assertIsNotNone(record)
        assert record is not None
        self.assertAlmostEqual(1.2, record.value)
        self.assertAlmostEqual(0.5, record.min_value)
        self.assertAlmostEqual(2.0, record.max_value)
        self.assertAlmostEqual(0.2, record.step)
        numeric_record_source = inspect.getsource(
            LibUVCControlBackend._numeric_record
        )
        self.assertIn("def scaled", numeric_record_source)

    def test_libuvc_device_matches_decorated_display_name(self) -> None:
        """Assert libuvc matches a decorated Qt display name to USB data."""

        class FakeDeviceDescriptor:
            """Expose the libuvc strings used by the matching helper."""

            serialNumber = None
            manufacturer = b"Sonix Technology Co., Ltd."
            product = b"A4ech FHD 1080P PC Camera"

        backend = object.__new__(LibUVCControlBackend)
        backend._lib = None
        backend._context = None
        descriptor = CameraDescriptor(
            stable_id="qt-camera::example",
            display_name="A4ech FHD 1080P PC Camera (Default)",
            backend_name="qt_multimedia",
            device_selector="qt-camera::example",
            native_identifier=None,
        )

        self.assertTrue(
            backend._device_matches_descriptor(
                FakeDeviceDescriptor(),
                descriptor,
                0,
            )
        )

    def test_libuvc_device_reference_survives_device_list_cleanup(
        self,
    ) -> None:
        """Assert libuvc keeps a matched device alive long enough to open."""

        class FakeDevice:
            """Expose one stable libuvc device pointer for the test."""

        class FakeDeviceDescriptor:
            """Expose the libuvc strings used by the matching helper."""

            serialNumber = None
            manufacturer = b"Sonix Technology Co., Ltd."
            product = b"A4ech FHD 1080P PC Camera"

        class FakeDeviceList:
            """Expose one libuvc-style device list for the test."""

            def __init__(self, device: object) -> None:
                """Store the single matching device pointer."""

                self._device = device

            def __getitem__(self, index: int) -> object | None:
                """Return the single device and then end the list."""

                if index == 0:
                    return self._device
                return None

        class FakeLibrary:
            """Record libuvc reference-management calls."""

            def __init__(self) -> None:
                """Initialize the recorded call log."""

                self.calls: list[tuple[str, object]] = []

            def uvc_ref_device(self, device: object) -> None:
                """Record the retained device pointer."""

                self.calls.append(("ref", device))

        backend = object.__new__(LibUVCControlBackend)
        backend._lib = FakeLibrary()
        backend._context = object()
        matched_device = FakeDevice()
        fake_device_list = FakeDeviceList(matched_device)
        backend._device_list = lambda: (fake_device_list, backend._context)
        backend._device_descriptor = lambda _device: FakeDeviceDescriptor()
        backend._device_matches_descriptor = (
            lambda _device_descriptor, _descriptor, _occurrence_index: True
        )
        freed_device_lists: list[object] = []
        backend._free_device_list = freed_device_lists.append
        descriptor = CameraDescriptor(
            stable_id="qt-camera::example",
            display_name="Example Camera",
            backend_name="qt_multimedia",
            device_selector="qt-camera::example",
        )

        device = backend._device_for_descriptor(descriptor)

        self.assertIs(device, matched_device)
        self.assertEqual([("ref", matched_device)], backend._lib.calls)
        self.assertEqual([fake_device_list], freed_device_lists)

    def test_libuvc_open_device_handle_releases_device_reference(
        self,
    ) -> None:
        """Assert libuvc releases the retained device after opening it."""

        class FakeLibrary:
            """Record libuvc open and release calls."""

            def __init__(self) -> None:
                """Initialize the recorded call log."""

                self.calls: list[tuple[str, object]] = []

            def uvc_open(
                self,
                device: object,
                handle_ptr: object,
            ) -> int:
                """Record the opened device and populate one fake handle."""

                self.calls.append(("open", device))
                handle_ptr = ctypes.cast(
                    handle_ptr,
                    ctypes.POINTER(ctypes.c_void_p),
                )
                handle_ptr[0] = ctypes.c_void_p(0x1234)
                return 0

            def uvc_unref_device(self, device: object) -> None:
                """Record the released device pointer."""

                self.calls.append(("unref", device))

        backend = object.__new__(LibUVCControlBackend)
        backend._lib = FakeLibrary()
        backend._context = object()
        device = object()

        handle = backend._open_device_handle(device)

        self.assertIsNotNone(handle)
        self.assertEqual(
            [("open", device), ("unref", device)],
            backend._lib.calls,
        )

    def test_qt_camera_control_backend_surfaces_common_controls(
        self,
    ) -> None:
        """Assert the Qt control backend applies native controls."""

        class FakeExposureMode:
            """Expose the Qt exposure-mode enum tokens used by the backend."""

            ExposureAuto = "ExposureAuto"
            ExposureManual = "ExposureManual"

        class FakeFocusMode:
            """Expose the Qt focus-mode enum tokens used by the backend."""

            FocusModeAuto = "FocusModeAuto"
            FocusModeManual = "FocusModeManual"

        class FakeWhiteBalanceMode:
            """Expose the Qt white-balance enum tokens used by the backend."""

            WhiteBalanceAuto = "WhiteBalanceAuto"
            WhiteBalanceManual = "WhiteBalanceManual"

        class FakeFlashMode:
            """Expose the Qt flash-mode enum tokens used by the backend."""

            FlashOff = "FlashOff"
            FlashOn = "FlashOn"
            FlashAuto = "FlashAuto"

        class FakeTorchMode:
            """Expose the Qt torch-mode enum tokens used by the backend."""

            TorchOff = "TorchOff"
            TorchOn = "TorchOn"
            TorchAuto = "TorchAuto"

        class FakeFeature:
            """Expose the Qt camera-feature bit flags used by the backend."""

            ExposureCompensation = 1
            FocusDistance = 2
            ColorTemperature = 4
            ManualExposureTime = 8
            IsoSensitivity = 16

        class FakeResolution:
            """Expose a Qt-like size object for the current camera format."""

            def __init__(self, width: int, height: int) -> None:
                """Store one stable resolution."""

                self._width = width
                self._height = height

            def width(self) -> int:
                """Return the recorded width."""

                return self._width

            def height(self) -> int:
                """Return the recorded height."""

                return self._height

        class FakeCameraFormat:
            """Expose the current Qt camera-format details."""

            def __init__(
                self,
                width: int,
                height: int,
                pixel_format: str,
                min_frame_rate: float,
                max_frame_rate: float,
            ) -> None:
                """Store one deterministic camera-format snapshot."""

                self._width = width
                self._height = height
                self._pixel_format = pixel_format
                self._min_frame_rate = min_frame_rate
                self._max_frame_rate = max_frame_rate

            def resolution(self) -> FakeResolution:
                """Return the active format resolution."""

                return FakeResolution(self._width, self._height)

            def pixelFormat(self) -> str:
                """Return the active format token."""

                return self._pixel_format

            def minFrameRate(self) -> float:
                """Return the lowest frame rate in the active format."""

                return self._min_frame_rate

            def maxFrameRate(self) -> float:
                """Return the highest frame rate in the active format."""

                return self._max_frame_rate

        class FakeCameraDevice:
            """Expose the video formats supported by the fake camera."""

            def __init__(self) -> None:
                """Store one deterministic format list."""

                self._formats = (
                    FakeCameraFormat(
                        1920,
                        1080,
                        "PixelFormat.Format_NV12",
                        30.0,
                        60.0,
                    ),
                    FakeCameraFormat(
                        1280,
                        720,
                        "PixelFormat.Format_NV12",
                        30.0,
                        30.0,
                    ),
                )
                self._camera_format = self._formats[0]

            def videoFormats(self) -> tuple[FakeCameraFormat, ...]:
                """Return the supported video formats."""

                return self._formats

            def cameraFormat(self) -> FakeCameraFormat:
                """Return the currently selected camera format."""

                return self._camera_format

        class FakeQCamera:
            """Record every camera-control call made by the backend."""

            Feature = FakeFeature
            ExposureMode = FakeExposureMode
            FocusMode = FakeFocusMode
            WhiteBalanceMode = FakeWhiteBalanceMode
            FlashMode = FakeFlashMode
            TorchMode = FakeTorchMode
            calls: list[tuple[str, object]] = []

            def __init__(self, device: object) -> None:
                """Initialize the fake camera with deterministic values."""

                self.device = device
                self._camera_format = getattr(
                    device, "cameraFormat", lambda: None
                )()

            def supportedFeatures(self) -> int:
                """Return every feature flag used by the test."""

                return (
                    FakeFeature.ExposureCompensation
                    | FakeFeature.FocusDistance
                    | FakeFeature.ColorTemperature
                    | FakeFeature.ManualExposureTime
                )

            def isExposureModeSupported(self, mode: object) -> bool:
                """Report support for the auto and manual exposure modes."""

                return mode in {
                    FakeExposureMode.ExposureAuto,
                    FakeExposureMode.ExposureManual,
                }

            def exposureMode(self) -> object:
                """Return the current exposure mode."""

                return FakeExposureMode.ExposureAuto

            def setExposureMode(self, mode: object) -> None:
                """Record the requested exposure mode."""

                self.calls.append(("setExposureMode", mode))

            def exposureCompensation(self) -> float:
                """Return the current exposure compensation."""

                return 0.0

            def setExposureCompensation(self, value: float) -> None:
                """Record the requested exposure compensation."""

                self.calls.append(("setExposureCompensation", value))

            def minimumExposureTime(self) -> float:
                """Return the minimum manual exposure time."""

                return 0.0005

            def maximumExposureTime(self) -> float:
                """Return the maximum manual exposure time."""

                return 0.5

            def manualExposureTime(self) -> float:
                """Return the current manual exposure time."""

                return 0.02

            def setManualExposureTime(self, value: float) -> None:
                """Record the requested manual exposure time."""

                self.calls.append(("setManualExposureTime", value))

            def minimumIsoSensitivity(self) -> float:
                """Return the minimum manual ISO sensitivity."""

                return 100.0

            def maximumIsoSensitivity(self) -> float:
                """Return the maximum manual ISO sensitivity."""

                return 1600.0

            def manualIsoSensitivity(self) -> float:
                """Return the current manual ISO sensitivity."""

                return 100.0

            def setManualIsoSensitivity(self, value: int) -> None:
                """Record the requested manual ISO sensitivity."""

                self.calls.append(("setManualIsoSensitivity", value))

            def isFocusModeSupported(self, mode: object) -> bool:
                """Report support for the auto and manual focus modes."""

                return mode in {
                    FakeFocusMode.FocusModeAuto,
                    FakeFocusMode.FocusModeManual,
                }

            def focusMode(self) -> object:
                """Return the current focus mode."""

                return FakeFocusMode.FocusModeAuto

            def setFocusMode(self, mode: object) -> None:
                """Record the requested focus mode."""

                self.calls.append(("setFocusMode", mode))

            def focusDistance(self) -> float:
                """Return the current focus distance."""

                return 0.5

            def setFocusDistance(self, value: float) -> None:
                """Record the requested focus distance."""

                self.calls.append(("setFocusDistance", value))

            def isWhiteBalanceModeSupported(self, mode: object) -> bool:
                """Report support for the white-balance modes."""

                return mode in {
                    FakeWhiteBalanceMode.WhiteBalanceAuto,
                    FakeWhiteBalanceMode.WhiteBalanceManual,
                }

            def whiteBalanceMode(self) -> object:
                """Return the current white-balance mode."""

                return FakeWhiteBalanceMode.WhiteBalanceAuto

            def setWhiteBalanceMode(self, mode: object) -> None:
                """Record the requested white-balance mode."""

                self.calls.append(("setWhiteBalanceMode", mode))

            def colorTemperature(self) -> float:
                """Return the current manual color temperature."""

                return 2800.0

            def setColorTemperature(self, value: int) -> None:
                """Record the requested color temperature."""

                self.calls.append(("setColorTemperature", value))

            def isFlashModeSupported(self, mode: object) -> bool:
                """Report support for the flash modes."""

                return mode in {
                    FakeFlashMode.FlashOff,
                    FakeFlashMode.FlashOn,
                    FakeFlashMode.FlashAuto,
                }

            def flashMode(self) -> object:
                """Return the current flash mode."""

                return FakeFlashMode.FlashOff

            def setFlashMode(self, mode: object) -> None:
                """Record the requested flash mode."""

                self.calls.append(("setFlashMode", mode))

            def isTorchModeSupported(self, mode: object) -> bool:
                """Report support for the torch modes."""

                return mode in {
                    FakeTorchMode.TorchOff,
                    FakeTorchMode.TorchOn,
                    FakeTorchMode.TorchAuto,
                }

            def torchMode(self) -> object:
                """Return the current torch mode."""

                return FakeTorchMode.TorchOff

            def setTorchMode(self, mode: object) -> None:
                """Record the requested torch mode."""

                self.calls.append(("setTorchMode", mode))

            def minimumZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maximumZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 4.0

            def zoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 2.0

            def setZoomFactor(self, value: float) -> None:
                """Record the requested zoom factor."""

                self.calls.append(("setZoomFactor", value))

            def cameraFormat(self) -> FakeCameraFormat:
                """Return the active camera format."""

                return self._camera_format

            def setCameraFormat(self, camera_format: FakeCameraFormat) -> None:
                """Record the requested active camera format."""

                self._camera_format = camera_format
                self.calls.append(("setCameraFormat", camera_format))

            def setAutoExposureTime(self) -> None:
                """Record the auto-exposure-time reset."""

                self.calls.append(("setAutoExposureTime", True))

            def setAutoIsoSensitivity(self) -> None:
                """Record the auto-ISO reset."""

                self.calls.append(("setAutoIsoSensitivity", True))

        fake_device = FakeCameraDevice()
        fake_qt_multimedia = mock.MagicMock(QCamera=FakeQCamera)
        preferred_source_formats: dict[str, str] = {}

        def get_preferred_source_format(
            descriptor: CameraDescriptor,
        ) -> str | None:
            """Return the remembered source-format token for one camera."""

            return preferred_source_formats.get(descriptor.stable_id)

        def set_preferred_source_format(
            descriptor: CameraDescriptor,
            token: str | None,
        ) -> None:
            """Store the preferred source-format token for one camera."""

            if token is None:
                preferred_source_formats.pop(descriptor.stable_id, None)
                return
            preferred_source_formats[descriptor.stable_id] = token

        descriptor = CameraDescriptor(
            stable_id="qt-camera::example",
            display_name="Example Camera",
            backend_name="qt_multimedia",
            device_selector="qt-camera::example",
        )
        backend = QtCameraControlBackend(
            fake_qt_multimedia,
            lambda _descriptor: fake_device,
            get_preferred_source_format,
            set_preferred_source_format,
        )

        controls = backend.list_controls(descriptor)
        controls_by_id = {control.control_id: control for control in controls}

        self.assertEqual(
            (
                "source_format",
                "exposure_mode",
                "exposure_locked",
                "backlight_compensation",
                "manual_exposure_time",
                "focus_auto",
                "focus_distance",
                "white_balance_automatic",
                "white_balance_temperature",
                "flash_mode",
                "torch_mode",
                "zoom_factor",
                "active_format",
                "restore_auto_exposure",
            ),
            tuple(control.control_id for control in controls),
        )
        self.assertEqual("enum", controls_by_id["source_format"].kind)
        self.assertEqual(2, len(controls_by_id["source_format"].choices))
        self.assertEqual(
            "numeric", controls_by_id["backlight_compensation"].kind
        )
        self.assertEqual("boolean", controls_by_id["focus_auto"].kind)
        self.assertEqual(
            "boolean", controls_by_id["white_balance_automatic"].kind
        )
        self.assertEqual("enum", controls_by_id["flash_mode"].kind)
        self.assertEqual("enum", controls_by_id["torch_mode"].kind)
        self.assertEqual("read_only", controls_by_id["active_format"].kind)
        self.assertIn("1920x1080", str(controls_by_id["active_format"].value))
        self.assertIn("fps", str(controls_by_id["active_format"].value))

        source_format_choice = controls_by_id["source_format"].choices[1].value
        backend.set_control_value(
            descriptor,
            "source_format",
            source_format_choice,
        )
        updated_controls = backend.list_controls(descriptor)
        updated_by_id = {
            control.control_id: control for control in updated_controls
        }
        self.assertEqual(
            source_format_choice,
            updated_by_id["source_format"].value,
        )
        self.assertIn(
            "1280x720",
            str(updated_by_id["active_format"].value),
        )

        FakeQCamera.calls = []
        backend.set_control_value(descriptor, "exposure_locked", True)
        backend.set_control_value(descriptor, "backlight_compensation", 1.5)
        backend.set_control_value(descriptor, "manual_exposure_time", 0.05)
        backend.set_control_value(descriptor, "focus_auto", False)
        backend.set_control_value(descriptor, "focus_distance", 0.25)
        backend.set_control_value(descriptor, "white_balance_automatic", False)
        backend.set_control_value(
            descriptor, "white_balance_temperature", 5000
        )
        backend.set_control_value(descriptor, "flash_mode", "on")
        backend.set_control_value(descriptor, "torch_mode", "auto")
        backend.set_control_value(descriptor, "restore_auto_exposure", True)

        control_calls = [
            call for call in FakeQCamera.calls if call[0] != "setCameraFormat"
        ]
        self.assertEqual(
            [
                ("setExposureMode", FakeExposureMode.ExposureManual),
                ("setExposureCompensation", 1.5),
                ("setExposureMode", FakeExposureMode.ExposureManual),
                ("setManualExposureTime", 0.05),
                ("setFocusMode", FakeFocusMode.FocusModeManual),
                ("setFocusMode", FakeFocusMode.FocusModeManual),
                ("setFocusDistance", 0.25),
                (
                    "setWhiteBalanceMode",
                    FakeWhiteBalanceMode.WhiteBalanceManual,
                ),
                ("setColorTemperature", 5000),
                ("setFlashMode", FakeFlashMode.FlashOn),
                ("setTorchMode", FakeTorchMode.TorchAuto),
                ("setExposureMode", FakeExposureMode.ExposureAuto),
                ("setAutoExposureTime", True),
                ("setAutoIsoSensitivity", True),
            ],
            control_calls,
        )

    def test_qt_camera_control_backend_hides_featureless_native_methods(
        self,
    ) -> None:
        """Assert Qt hides method stubs when the feature flag is absent."""

        class FakeExposureMode:
            """Expose the Qt exposure-mode enum tokens used by the backend."""

            ExposureAuto = "ExposureAuto"
            ExposureManual = "ExposureManual"

        class FakeFocusMode:
            """Expose the Qt focus-mode enum tokens used by the backend."""

            FocusModeAuto = "FocusModeAuto"
            FocusModeManual = "FocusModeManual"

        class FakeWhiteBalanceMode:
            """Expose the Qt white-balance enum tokens used by the backend."""

            WhiteBalanceAuto = "WhiteBalanceAuto"
            WhiteBalanceManual = "WhiteBalanceManual"

        class FakeFeature:
            """Expose the Qt camera-feature bit flags used by the backend."""

            ExposureCompensation = 1
            FocusDistance = 2
            ColorTemperature = 4
            ManualExposureTime = 8

        class FakeCameraDevice:
            """Expose one deterministic camera device for the backend."""

            def cameraFormat(self) -> object | None:
                """Return no selected format for the featureless test."""

                return None

        class FakeQCamera:
            """Expose featureless stubs for the native-method fallback."""

            Feature = FakeFeature
            ExposureMode = FakeExposureMode
            FlashMode = FakeExposureMode
            FocusMode = FakeFocusMode
            TorchMode = FakeExposureMode
            WhiteBalanceMode = FakeWhiteBalanceMode

            def __init__(self, device: object) -> None:
                """Store the fake device for later method calls."""

                self.device = device

            def supportedFeatures(self) -> int:
                """Report no supported Qt camera features."""

                return 0

            def isExposureModeSupported(self, mode: object) -> bool:
                """Report only continuous auto exposure support."""

                return mode == FakeExposureMode.ExposureAuto

            def exposureMode(self) -> object:
                """Return the current exposure mode."""

                return FakeExposureMode.ExposureAuto

            def isFocusModeSupported(self, mode: object) -> bool:
                """Report no writable focus support."""

                return False

            def isWhiteBalanceModeSupported(self, mode: object) -> bool:
                """Report only auto white-balance support."""

                return mode == FakeWhiteBalanceMode.WhiteBalanceAuto

            def whiteBalanceMode(self) -> object:
                """Return the current white-balance mode."""

                return FakeWhiteBalanceMode.WhiteBalanceAuto

            def minimumZoomFactor(self) -> float:
                """Return a fixed minimum zoom factor."""

                return 1.0

            def maximumZoomFactor(self) -> float:
                """Return a fixed maximum zoom factor."""

                return 1.0

            def zoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def cameraFormat(self) -> object | None:
                """Return no selected camera format for this test."""

                return None

        fake_qt_multimedia = mock.MagicMock(QCamera=FakeQCamera)
        backend = QtCameraControlBackend(
            fake_qt_multimedia,
            lambda _descriptor: FakeCameraDevice(),
        )
        descriptor = CameraDescriptor(
            stable_id="qt-camera::featureless",
            display_name="Featureless Camera",
            backend_name="qt_multimedia",
            device_selector="qt-camera::featureless",
        )

        control_ids = {
            control.control_id for control in backend.list_controls(descriptor)
        }

        self.assertNotIn("backlight_compensation", control_ids)
        self.assertNotIn("manual_exposure_time", control_ids)
        self.assertNotIn("focus_distance", control_ids)
        self.assertNotIn("white_balance_temperature", control_ids)

    @mock.patch.object(
        QtCameraBackend,
        "_camera_device_for_descriptor",
        autospec=True,
    )
    @mock.patch("webcam_micro.camera._load_qt_camera_modules")
    def test_qt_camera_backend_uses_preferred_source_format_on_open_session(
        self,
        load_modules: mock.MagicMock,
        camera_device_for_descriptor: mock.MagicMock,
    ) -> None:
        """Assert the Qt backend opens sessions with the chosen resolution."""

        class FakeResolution:
            """Expose a Qt-like size object for the test formats."""

            def __init__(self, width: int, height: int) -> None:
                """Store one stable resolution."""

                self._width = width
                self._height = height

            def width(self) -> int:
                """Return the recorded width."""

                return self._width

            def height(self) -> int:
                """Return the recorded height."""

                return self._height

        class FakeCameraFormat:
            """Expose the supported Qt camera formats."""

            def __init__(
                self,
                width: int,
                height: int,
                pixel_format: str,
                min_frame_rate: float,
                max_frame_rate: float,
            ) -> None:
                """Store one stable format snapshot."""

                self._width = width
                self._height = height
                self._pixel_format = pixel_format
                self._min_frame_rate = min_frame_rate
                self._max_frame_rate = max_frame_rate

            def resolution(self) -> FakeResolution:
                """Return the active format resolution."""

                return FakeResolution(self._width, self._height)

            def pixelFormat(self) -> str:
                """Return the active format token."""

                return self._pixel_format

            def minFrameRate(self) -> float:
                """Return the lowest frame rate in the active format."""

                return self._min_frame_rate

            def maxFrameRate(self) -> float:
                """Return the highest frame rate in the active format."""

                return self._max_frame_rate

        class FakeCameraDevice:
            """Expose one deterministic camera device for the backend."""

            def __init__(self) -> None:
                """Store the supported video formats."""

                self._formats = (
                    FakeCameraFormat(
                        1920,
                        1080,
                        "PixelFormat.Format_NV12",
                        30.0,
                        60.0,
                    ),
                    FakeCameraFormat(
                        1280,
                        720,
                        "PixelFormat.Format_NV12",
                        30.0,
                        30.0,
                    ),
                )

            def videoFormats(self) -> tuple[FakeCameraFormat, ...]:
                """Return the supported video formats."""

                return self._formats

        class FakeSession:
            """Record the camera format used to open one session."""

            last_camera_format: object | None = None

            def __init__(
                self,
                descriptor: CameraDescriptor,
                camera_device: object,
                *,
                camera_format: object | None = None,
                qt_core: object,
                qt_gui: object,
                qt_multimedia: object,
            ) -> None:
                """Store the session inputs for later assertions."""

                self.descriptor = descriptor
                self.camera_device = camera_device
                self.camera_format = camera_format
                FakeSession.last_camera_format = camera_format

        fake_device = FakeCameraDevice()
        fake_qt_multimedia = mock.MagicMock()
        load_modules.return_value = (object(), object(), fake_qt_multimedia)
        camera_device_for_descriptor.return_value = fake_device

        backend = QtCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="qt-camera::example",
            display_name="Example Camera",
            backend_name="qt_multimedia",
            device_selector="qt-camera::example",
        )
        selected_format = "1280x720|Format_NV12|30fps"
        backend.set_control_value(descriptor, "source_format", selected_format)
        expected_format = fake_device.videoFormats()[1]

        with mock.patch("webcam_micro.camera.QtCameraSession", FakeSession):
            session = backend.open_session(descriptor)

        self.assertIsInstance(session, FakeSession)
        self.assertEqual(descriptor, session.descriptor)
        self.assertIs(expected_format, FakeSession.last_camera_format)
        self.assertIs(expected_format, session.camera_format)

    def test_linux_v4l2_control_backend_surfaces_light_and_vendor_controls(
        self,
    ) -> None:
        """Assert the Linux V4L2 backend keeps light and vendor controls."""

        class FakeBackend(LinuxV4L2CameraControlBackend):
            """Expose deterministic V4L2 records without touching hardware."""

            def __init__(self) -> None:
                """Store one fake resolver for the device node."""

                super().__init__(lambda _descriptor: "/dev/video-test")

            def _records_for_descriptor(
                self,
                descriptor: CameraDescriptor,
            ) -> tuple[_V4L2ControlRecord, ...]:
                """Return the synthetic V4L2 controls used by this test."""

                return (
                    _V4L2ControlRecord(
                        control_id="brightness",
                        label="Brightness",
                        kind="numeric",
                        query_id=101,
                        value=64,
                        min_value=0.0,
                        max_value=255.0,
                        step=1.0,
                        details="Linux V4L2 control `Brightness`.",
                    ),
                    _V4L2ControlRecord(
                        control_id="power_line_frequency",
                        label="Power Line Frequency",
                        kind="enum",
                        query_id=102,
                        value="50",
                        choices=(
                            CameraControlChoice(
                                value="disabled",
                                label="Disabled",
                            ),
                            CameraControlChoice(value="50", label="50 Hz"),
                            CameraControlChoice(value="60", label="60 Hz"),
                            CameraControlChoice(value="auto", label="Auto"),
                        ),
                        menu_values=(0, 1, 2, 3),
                        details="Linux V4L2 control `Power Line Frequency`.",
                    ),
                    _V4L2ControlRecord(
                        control_id="activity_led",
                        label="Activity LED",
                        kind="boolean",
                        query_id=103,
                        value=False,
                        details="Linux V4L2 control `Activity LED`.",
                    ),
                    _V4L2ControlRecord(
                        control_id="vendor_extension",
                        label="Vendor Extension",
                        kind="read_only",
                        query_id=104,
                        value="Enabled",
                        read_only=True,
                        enabled=False,
                        details="Linux V4L2 control `Vendor Extension`.",
                    ),
                )

        backend = FakeBackend()
        descriptor = CameraDescriptor(
            stable_id="linux-v4l2::example",
            display_name="Microscope Camera",
            backend_name="ffmpeg",
            device_selector="/dev/video-test",
        )

        controls = backend.list_controls(descriptor)
        controls_by_id = {control.control_id: control for control in controls}

        self.assertEqual(
            (
                "brightness",
                "power_line_frequency",
                "activity_led",
                "vendor_extension",
            ),
            tuple(control.control_id for control in controls),
        )
        self.assertEqual("numeric", controls_by_id["brightness"].kind)
        self.assertEqual("enum", controls_by_id["power_line_frequency"].kind)
        self.assertEqual("boolean", controls_by_id["activity_led"].kind)
        self.assertTrue(controls_by_id["vendor_extension"].read_only)
        self.assertIn(
            "60 Hz",
            [
                choice.label
                for choice in controls_by_id["power_line_frequency"].choices
            ],
        )

        write_calls: list[tuple[int, int, int]] = []

        def record_v4l2_write(
            device_fd: int,
            query_id: int,
            value: int,
        ) -> None:
            """Record the synthetic V4L2 writes for this test."""

            write_calls.append((device_fd, query_id, value))

        with (
            mock.patch(
                "webcam_micro.camera.os.open",
                return_value=7,
            ),
            mock.patch(
                "webcam_micro.camera.os.close",
                return_value=None,
            ),
            mock.patch(
                "webcam_micro.camera._v4l2_write_control_value",
                side_effect=record_v4l2_write,
            ),
        ):
            backend.set_control_value(descriptor, "brightness", 12)
            backend.set_control_value(descriptor, "power_line_frequency", "60")
            backend.set_control_value(descriptor, "activity_led", True)
            with self.assertRaises(CameraControlApplyError):
                backend.set_control_value(
                    descriptor,
                    "vendor_extension",
                    "Enabled",
                )

        self.assertEqual(
            [
                (7, 101, 12),
                (7, 102, 2),
                (7, 103, 1),
            ],
            write_calls,
        )

    def test_selected_control_backend_uses_one_owner_only(
        self,
    ) -> None:
        """Assert the selected backend keeps one control owner."""

        class PrimaryBackend:
            """Expose one primary control and record writes."""

            def __init__(self) -> None:
                """Initialize the test bookkeeping."""

                self.calls: list[tuple[str, str, object]] = []

            def list_controls(
                self,
                descriptor: CameraDescriptor,
            ) -> tuple[CameraControl, ...]:
                """Return the primary control surface."""

                return (
                    CameraControl(
                        control_id="exposure_mode",
                        label="Exposure Mode",
                        kind="enum",
                        value="continuous_auto",
                    ),
                )

            def set_control_value(
                self,
                descriptor: CameraDescriptor,
                control_id: str,
                value: object,
            ) -> None:
                """Record the primary update."""

                self.calls.append(("set", control_id, value))

            def trigger_control_action(
                self,
                descriptor: CameraDescriptor,
                control_id: str,
            ) -> None:
                """Record the primary action."""

                self.calls.append(("action", control_id, True))

        class SecondaryBackend:
            """Expose extra controls that the primary backend lacks."""

            def __init__(self) -> None:
                """Initialize the test bookkeeping."""

                self.calls: list[tuple[str, str, object]] = []

            def list_controls(
                self,
                descriptor: CameraDescriptor,
            ) -> tuple[CameraControl, ...]:
                """Return the extra control surface."""

                return (
                    CameraControl(
                        control_id="brightness",
                        label="Brightness",
                        kind="numeric",
                        value=12,
                    ),
                    CameraControl(
                        control_id="vendor_extension",
                        label="Vendor Extension",
                        kind="read_only",
                        value="Enabled",
                    ),
                )

            def set_control_value(
                self,
                descriptor: CameraDescriptor,
                control_id: str,
                value: object,
            ) -> None:
                """Record the secondary update."""

                self.calls.append(("set", control_id, value))

            def trigger_control_action(
                self,
                descriptor: CameraDescriptor,
                control_id: str,
            ) -> None:
                """Record the secondary action."""

                self.calls.append(("action", control_id, True))

        primary = PrimaryBackend()
        secondary = SecondaryBackend()
        backend = _SelectedCameraControlBackend(primary, secondary)
        descriptor = CameraDescriptor(
            stable_id="selected::example",
            display_name="Selected Camera",
            backend_name="qt_multimedia",
            device_selector="selected::example",
        )

        controls = backend.list_controls(descriptor)
        self.assertEqual(
            ("exposure_mode",),
            tuple(control.control_id for control in controls),
        )

        backend.set_control_value(descriptor, "exposure_mode", "locked")
        backend.trigger_control_action(descriptor, "exposure_mode")

        self.assertEqual([], secondary.calls)
        self.assertEqual(
            [
                ("set", "exposure_mode", "locked"),
                ("action", "exposure_mode", True),
            ],
            primary.calls,
        )

    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_build_control_backend_selects_one_backend_on_macos(
        self,
    ) -> None:
        """Assert the macOS backend selection keeps one control owner."""

        native_backend = mock.MagicMock()
        qt_backend = mock.MagicMock()
        av_backend = mock.MagicMock()
        native_backend.list_controls.return_value = (
            CameraControl(
                control_id="manual_exposure_time",
                label="Manual Exposure Time",
                kind="numeric",
                value=0.05,
            ),
        )
        qt_backend.list_controls.return_value = (
            CameraControl(
                control_id="brightness",
                label="Brightness",
                kind="numeric",
                value=12,
            ),
        )
        av_backend.list_controls.return_value = (
            CameraControl(
                control_id="vendor_extension",
                label="Vendor Extension",
                kind="read_only",
                value="Enabled",
            ),
        )

        with (
            mock.patch(
                "webcam_micro.camera.LibUVCControlBackend",
                return_value=native_backend,
            ),
            mock.patch(
                "webcam_micro.camera.QtCameraControlBackend",
                return_value=qt_backend,
            ),
            mock.patch(
                "webcam_micro.camera.AvFoundationCameraControlBackend",
                return_value=av_backend,
            ),
        ):
            backend = _build_control_backend(
                object(),
                lambda _descriptor: object(),
                None,
            )

        controls = backend.list_controls(
            CameraDescriptor(
                stable_id="macos::example",
                display_name="Mac Camera",
                backend_name="qt_multimedia",
                device_selector="macos::example",
            ),
        )
        self.assertEqual(
            ("manual_exposure_time",),
            tuple(control.control_id for control in controls),
        )

        descriptor = CameraDescriptor(
            stable_id="macos::example",
            display_name="Mac Camera",
            backend_name="qt_multimedia",
            device_selector="macos::example",
        )

        backend.set_control_value(
            descriptor,
            "manual_exposure_time",
            0.05,
        )

        native_backend.set_control_value.assert_called_once_with(
            descriptor,
            "manual_exposure_time",
            0.05,
        )
        qt_backend.set_control_value.assert_not_called()
        av_backend.set_control_value.assert_not_called()

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_control_surface_exposes_native_mac_controls(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert the macOS control surface exposes native controls."""

        class FakeCMTime:
            """Provide a minimal CMTime-compatible structure."""

            def __init__(
                self,
                value: int,
                timescale: int,
                *_unused: object,
            ) -> None:
                """Store the CMTime fields used by the backend."""

                self.field_0 = value
                self.field_1 = timescale

        class FakeTemperatureTintValues:
            """Provide a minimal white-balance temperature/tint struct."""

            def __init__(self, temperature: float, tint: float) -> None:
                """Store the white-balance values used by the backend."""

                self.field_0 = temperature
                self.field_1 = tint

        class FakeExposureBiasRange:
            """Provide the recommended macOS exposure-bias range."""

            def __init__(self) -> None:
                """Store one stable range for the control surface."""

                self.minExposureBias = -2.0
                self.maxExposureBias = 2.0

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __init__(self) -> None:
                """Store one stable active-format snapshot."""

                self.minExposureDuration = FakeCMTime(1, 120)
                self.maxExposureDuration = FakeCMTime(1, 2)
                self.minISO = 80.0
                self.maxISO = 640.0
                self.systemRecommendedExposureBiasRange = (
                    FakeExposureBiasRange()
                )
                self._video_hdr_supported = False

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

            def isVideoHDRSupported(self) -> bool:
                """Report whether this format supports video HDR."""

                return self._video_hdr_supported

        class FakeDevice:
            """Provide the AVFoundation surface used by the backend."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()
                self._white_balance_gains = object()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Microscope Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-1"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable exposure modes."""

                return mode_value in {0, 1, 2, 3}

            def exposureMode(self) -> int:
                """Return the current writable exposure mode."""

                return 2

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def exposureDuration(self) -> FakeCMTime:
                """Return the current exposure duration."""

                return FakeCMTime(1, 60)

            def ISO(self) -> float:
                """Return the current ISO value."""

                return 160.0

            def minExposureTargetBias(self) -> float:
                """Return the minimum exposure compensation."""

                return -4.0

            def maxExposureTargetBias(self) -> float:
                """Return the maximum exposure compensation."""

                return 4.0

            def exposureTargetBias(self) -> float:
                """Return the current exposure compensation."""

                return 0.5

            def isFocusModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable focus modes."""

                return mode_value in {0, 1, 2}

            def focusMode(self) -> int:
                """Return the current focus mode."""

                return 2

            def lensPosition(self) -> float:
                """Return the current manual lens position."""

                return 0.25

            def isWhiteBalanceModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable white-balance modes."""

                return mode_value in {0, 1, 2}

            def whiteBalanceMode(self) -> int:
                """Return the current white-balance mode."""

                return 2

            def deviceWhiteBalanceGains(self) -> object:
                """Return one white-balance gains snapshot."""

                return self._white_balance_gains

            def temperatureAndTintValuesForDeviceWhiteBalanceGains_(
                self,
                gains: object,
            ) -> FakeTemperatureTintValues:
                """Convert gains into one temperature/tint structure."""

                return FakeTemperatureTintValues(3000.0, 0.0)

            def isFlashModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable flash modes."""

                return mode_value in {0, 1, 2}

            def flashMode(self) -> int:
                """Return the current flash mode."""

                return 2

            def isTorchModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable torch modes."""

                return mode_value in {0, 1, 2}

            def torchMode(self) -> int:
                """Return the current torch mode."""

                return 2

            def isSmoothAutoFocusEnabled(self) -> bool:
                """Return whether smooth autofocus is enabled."""

                return True

            def isSmoothAutoFocusSupported(self) -> bool:
                """Report support for smooth autofocus."""

                return True

            def automaticallyAdjustsVideoHDREnabled(self) -> bool:
                """Return whether automatic video HDR is enabled."""

                return False

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 4.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 2.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def setExposureMode_(self, mode_value: int) -> None:
                """Accept exposure updates in the test double."""

                self.calls.append(("setExposureMode", mode_value))

            def setExposureModeCustomWithDuration_ISO_completionHandler_(
                self,
                duration: FakeCMTime,
                iso_value: float,
                completion: object,
            ) -> None:
                """Accept custom exposure updates in the test double."""

                self.calls.append(
                    (
                        "setExposureModeCustom",
                        round(duration.field_0 / duration.field_1, 6),
                        iso_value,
                    )
                )
                _invoke_completion(completion)

            def setExposureTargetBias_completionHandler_(
                self,
                compensation: float,
                completion: object,
            ) -> None:
                """Accept exposure-compensation updates."""

                self.calls.append(("setExposureTargetBias", compensation))
                _invoke_completion(completion)

            def setFocusMode_(self, mode_value: int) -> None:
                """Accept focus updates in the test double."""

                self.calls.append(("setFocusMode", mode_value))

            def setFocusModeLockedWithLensPosition_completionHandler_(
                self,
                position: float,
                completion: object,
            ) -> None:
                """Accept manual focus updates in the test double."""

                self.calls.append(("setFocusDistance", position))
                _invoke_completion(completion)

            def setWhiteBalanceMode_(self, mode_value: int) -> None:
                """Accept white-balance updates in the test double."""

                self.calls.append(("setWhiteBalanceMode", mode_value))

            def set_white_balance_temperature(
                self,
                values: FakeTemperatureTintValues,
                completion: object,
            ) -> None:
                """Accept manual white-balance updates."""

                self.calls.append(
                    (
                        "setWhiteBalanceTemperature",
                        values.field_0,
                        values.field_1,
                    )
                )
                _invoke_completion(completion)

            locals()[
                "setWhiteBalanceModeLockedWithDeviceWhiteBalanceTemperatureAnd"
                "TintValues_completionHandler_"
            ] = set_white_balance_temperature

            def setFlashMode_(self, mode_value: int) -> None:
                """Accept flash updates in the test double."""

                self.calls.append(("setFlashMode", mode_value))

            def setTorchMode_(self, mode_value: int) -> None:
                """Accept torch updates in the test double."""

                self.calls.append(("setTorchMode", mode_value))

            def setSmoothAutoFocusEnabled_(self, enabled: bool) -> None:
                """Accept smooth-autofocus updates."""

                self.calls.append(("setSmoothAutoFocusEnabled", enabled))

            def setAutomaticallyAdjustsVideoHDREnabled_(
                self,
                enabled: bool,
            ) -> None:
                """Accept automatic HDR updates."""

                self.calls.append(
                    ("setAutomaticallyAdjustsVideoHDREnabled", enabled)
                )

            def setVideoZoomFactor_(self, zoom_value: float) -> None:
                """Accept zoom updates in the test double."""

                self.calls.append(("setVideoZoomFactor", zoom_value))

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-1",
            display_name="Microscope Camera",
            backend_name="avfoundation",
            device_selector="camera-1",
            native_identifier="camera-1",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertEqual(
            (
                "exposure_mode",
                "exposure_locked",
                "manual_exposure_time",
                "backlight_compensation",
                "focus_auto",
                "focus_distance",
                "white_balance_automatic",
                "white_balance_temperature",
                "flash_mode",
                "torch_mode",
                "zoom_factor",
                "active_format",
                "restore_auto_exposure",
            ),
            control_ids,
        )
        controls_by_id = {
            control.control_id: control
            for control in backend.list_controls(descriptor)
        }
        self.assertEqual(
            "numeric", controls_by_id["manual_exposure_time"].kind
        )
        self.assertEqual(
            "numeric", controls_by_id["backlight_compensation"].kind
        )
        self.assertEqual(
            -2.0, controls_by_id["backlight_compensation"].min_value
        )
        self.assertEqual(
            2.0, controls_by_id["backlight_compensation"].max_value
        )
        self.assertEqual("boolean", controls_by_id["focus_auto"].kind)
        self.assertEqual("numeric", controls_by_id["focus_distance"].kind)
        self.assertEqual(
            "boolean", controls_by_id["white_balance_automatic"].kind
        )
        self.assertEqual(
            "numeric", controls_by_id["white_balance_temperature"].kind
        )
        self.assertEqual("read_only", controls_by_id["active_format"].kind)
        self.assertEqual(
            "action", controls_by_id["restore_auto_exposure"].kind
        )
        self.assertNotIn("control_backend", control_ids)
        self.assertNotIn("low_light_boost_support", control_ids)
        self.assertNotIn("video_hdr_automatic", control_ids)

        device = FakeCaptureDeviceClass._device
        device.calls.clear()
        device._active_format._video_hdr_supported = True
        hdr_controls = {
            control.control_id: control
            for control in backend.list_controls(descriptor)
        }
        self.assertIn("video_hdr_automatic", hdr_controls)
        self.assertEqual("boolean", hdr_controls["video_hdr_automatic"].kind)
        backend.set_control_value(descriptor, "video_hdr_automatic", True)
        self.assertEqual(
            [("setAutomaticallyAdjustsVideoHDREnabled", True)],
            device.calls,
        )

        device.calls.clear()
        backend.set_control_value(descriptor, "exposure_locked", True)
        backend.set_control_value(descriptor, "manual_exposure_time", 0.05)
        backend.set_control_value(descriptor, "backlight_compensation", 1.5)
        backend.set_control_value(descriptor, "focus_auto", False)
        backend.set_control_value(descriptor, "focus_distance", 0.25)
        backend.set_control_value(descriptor, "white_balance_automatic", False)
        backend.set_control_value(
            descriptor,
            "white_balance_temperature",
            5000,
        )
        backend.set_control_value(descriptor, "flash_mode", "on")
        backend.set_control_value(descriptor, "torch_mode", "auto")
        backend.set_control_value(descriptor, "zoom_factor", 3.0)
        backend.set_control_value(descriptor, "restore_auto_exposure", True)

        self.assertEqual(
            [
                ("setExposureMode", 0),
                ("setExposureModeCustom", 0.05, 160.0),
                ("setExposureTargetBias", 1.5),
                ("setFocusMode", 0),
                ("setFocusDistance", 0.25),
                ("setWhiteBalanceMode", 0),
                ("setWhiteBalanceTemperature", 5000.0, 0.0),
                ("setFlashMode", 1),
                ("setTorchMode", 2),
                ("setVideoZoomFactor", 3.0),
                ("setExposureMode", 2),
            ],
            device.calls,
        )

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_exposure_lock_visible_without_continuous_auto(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert exposure lock stays visible when only auto is supported."""

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

        class FakeDevice:
            """Provide the AVFoundation surface used by the backend."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Microscope Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-lock-only-auto"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support for lock and auto exposure modes only."""

                return mode_value in {0, 1}

            def exposureMode(self) -> int:
                """Return the current writable exposure mode."""

                return 1

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def minExposureTargetBias(self) -> float:
                """Return the minimum exposure compensation."""

                return -4.0

            def maxExposureTargetBias(self) -> float:
                """Return the maximum exposure compensation."""

                return 4.0

            def exposureTargetBias(self) -> float:
                """Return the current exposure compensation."""

                return 0.5

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 2.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def setExposureMode_(self, mode_value: int) -> None:
                """Record exposure-mode updates."""

                self.calls.append(("setExposureMode", mode_value))

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-lock-only-auto",
            display_name="Microscope Camera",
            backend_name="avfoundation",
            device_selector="camera-lock-only-auto",
            native_identifier="camera-lock-only-auto",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertIn("exposure_locked", control_ids)
        self.assertIn("restore_auto_exposure", control_ids)

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_skips_unsupported_smooth_auto_focus(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert unsupported smooth autofocus stays hidden on macOS."""

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

        class FakeDevice:
            """Provide the AVFoundation surface used by the backend."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Microscope Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-no-smooth-autofocus"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support only for plain auto exposure."""

                return mode_value == 1

            def exposureMode(self) -> int:
                """Return the current writable exposure mode."""

                return 1

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 2.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def isSmoothAutoFocusEnabled(self) -> bool:
                """Fail if unsupported smooth autofocus is probed."""

                raise AssertionError("unsupported smooth autofocus was probed")

            def setSmoothAutoFocusEnabled_(self, enabled: bool) -> None:
                """Record smooth-autofocus updates if they were ever routed."""

                self.calls.append(("setSmoothAutoFocusEnabled", enabled))

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-no-smooth-autofocus",
            display_name="Microscope Camera",
            backend_name="avfoundation",
            device_selector="camera-no-smooth-autofocus",
            native_identifier="camera-no-smooth-autofocus",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertNotIn("smooth_auto_focus", control_ids)

    @mock.patch("webcam_micro.camera.wrap_completion_handler")
    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_manual_exposure_rejects_unsupported_custom_exposure(
        self,
        load_modules: mock.MagicMock,
        wrap_completion_handler: mock.MagicMock,
    ) -> None:
        """Assert unsupported custom exposure fails closed on macOS."""

        class FakeDevice:
            """Provide the minimal AVFoundation surface used by the backend."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Microscope Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-1"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support only for the non-custom exposure modes."""

                return mode_value in {0, 1, 2}

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-1",
            display_name="Microscope Camera",
            backend_name="avfoundation",
            device_selector="camera-1",
            native_identifier="camera-1",
        )

        device = FakeCaptureDeviceClass._device
        with self.assertRaises(CameraControlApplyError):
            backend.set_control_value(descriptor, "manual_exposure_time", 0.05)

        wrap_completion_handler.assert_not_called()
        self.assertEqual([], device.calls)

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_control_surface_skips_unsupported_bias(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert unsupported exposure bias never reaches the setter."""

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

        class FakeDevice:
            """Provide the unsupported AVFoundation surface."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Unsupported Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-unsupported"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support only for plain auto exposure."""

                return mode_value == 1

            def exposureMode(self) -> int:
                """Return the current writable exposure mode."""

                return 1

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def minExposureTargetBias(self) -> float:
                """Return the minimum exposure compensation."""

                return -4.0

            def maxExposureTargetBias(self) -> float:
                """Return the maximum exposure compensation."""

                return 4.0

            def exposureTargetBias(self) -> float:
                """Return the current exposure compensation."""

                return 0.5

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 2.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def setExposureTargetBias_completionHandler_(
                self,
                compensation: float,
                completion: object,
            ) -> None:
                """Record exposure-compensation updates."""

                self.calls.append(("setExposureTargetBias", compensation))
                _invoke_completion(completion)

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-unsupported",
            display_name="Unsupported Camera",
            backend_name="avfoundation",
            device_selector="camera-unsupported",
            native_identifier="camera-unsupported",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertNotIn("backlight_compensation", control_ids)

        with self.assertRaises(CameraControlApplyError):
            backend.set_control_value(
                descriptor,
                "backlight_compensation",
                1.5,
            )

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_control_surface_skips_unsupported_white_balance(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert unsupported white-balance temperature stays hidden."""

        class FakeTemperatureTintValues:
            """Provide a minimal white-balance temperature/tint struct."""

            def __init__(self, temperature: float, tint: float) -> None:
                """Store the white-balance values used by the backend."""

                self.field_0 = temperature
                self.field_1 = tint

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

        class FakeDevice:
            """Provide the unsupported AVFoundation surface."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()
                self._white_balance_gains = object()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Unsupported White Balance Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-white-balance-unsupported"

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def isWhiteBalanceModeSupported_(self, mode_value: int) -> bool:
                """Report support only for the auto white-balance modes."""

                return mode_value in {1, 2}

            def whiteBalanceMode(self) -> int:
                """Return the current white-balance mode."""

                return 1

            def deviceWhiteBalanceGains(self) -> object:
                """Return one white-balance gains snapshot."""

                return self._white_balance_gains

            def temperatureAndTintValuesForDeviceWhiteBalanceGains_(
                self,
                gains: object,
            ) -> FakeTemperatureTintValues:
                """Convert gains into one temperature/tint structure."""

                return FakeTemperatureTintValues(3000.0, 0.0)

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 2.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def set_white_balance_temperature(
                self,
                values: FakeTemperatureTintValues,
                completion: object,
            ) -> None:
                """Record white-balance updates."""

                self.calls.append(
                    ("setWhiteBalanceTemperature", values.field_0)
                )
                _invoke_completion(completion)

            locals()[
                "setWhiteBalanceModeLockedWithDeviceWhiteBalanceTemperatureAnd"
                "TintValues_completionHandler_"
            ] = set_white_balance_temperature

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-white-balance-unsupported",
            display_name="Unsupported White Balance Camera",
            backend_name="avfoundation",
            device_selector="camera-white-balance-unsupported",
            native_identifier="camera-white-balance-unsupported",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertNotIn("white_balance_automatic", control_ids)
        self.assertNotIn("white_balance_temperature", control_ids)

        with self.assertRaises(CameraControlApplyError):
            backend.set_control_value(
                descriptor,
                "white_balance_temperature",
                5000,
            )

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_white_balance_custom_gains_support(
        self, load_modules: mock.MagicMock
    ) -> None:
        """Assert custom-gains white balance exposes the manual controls."""

        class FakeTemperatureTintValues:
            """Provide a minimal white-balance temperature/tint struct."""

            def __init__(self, temperature: float, tint: float) -> None:
                """Store the white-balance values used by the backend."""

                self.field_0 = temperature
                self.field_1 = tint

        class FakeActiveFormat:
            """Expose the AVFoundation format metadata used by the backend."""

            def __str__(self) -> str:
                """Return a readable active-format summary."""

                return "1920x1080 30 FPS (MJPEG)"

        class FakeDevice:
            """Provide the AVFoundation surface used by the backend."""

            def __init__(self) -> None:
                """Store the current test-double state and call log."""

                self.calls: list[tuple[object, ...]] = []
                self._active_format = FakeActiveFormat()
                self._white_balance_gains = object()

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Custom Gains White Balance Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for matching."""

                return "camera-white-balance-custom-gains"

            def activeFormat(self) -> FakeActiveFormat:
                """Return the current active camera format."""

                return self._active_format

            def isWhiteBalanceModeSupported_(self, mode_value: int) -> bool:
                """Report support only for the auto white-balance modes."""

                return mode_value in {1, 2}

            def isLockingWhiteBalanceWithCustomDeviceGainsSupported(
                self,
            ) -> bool:
                """Report support for custom-gains white-balance locking."""

                return True

            def whiteBalanceMode(self) -> int:
                """Return the current white-balance mode."""

                return 1

            def deviceWhiteBalanceGains(self) -> object:
                """Return one white-balance gains snapshot."""

                return self._white_balance_gains

            def temperatureAndTintValuesForDeviceWhiteBalanceGains_(
                self,
                gains: object,
            ) -> FakeTemperatureTintValues:
                """Convert gains into one temperature/tint structure."""

                return FakeTemperatureTintValues(3100.0, 0.0)

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 2.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 1.0

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def set_white_balance_temperature(
                self,
                values: FakeTemperatureTintValues,
                completion: object,
            ) -> None:
                """Record white-balance updates."""

                self.calls.append(
                    ("setWhiteBalanceTemperature", values.field_0)
                )
                _invoke_completion(completion)

            locals()[
                "setWhiteBalanceModeLockedWithDeviceWhiteBalanceTemperatureAnd"
                "TintValues_completionHandler_"
            ] = set_white_balance_temperature

            def setWhiteBalanceMode_(self, mode_value: int) -> None:
                """Record white-balance mode updates."""

                self.calls.append(("setWhiteBalanceMode", mode_value))

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            _device = FakeDevice()

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeCaptureDeviceClass._device,)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-white-balance-custom-gains",
            display_name="Custom Gains White Balance Camera",
            backend_name="avfoundation",
            device_selector="camera-white-balance-custom-gains",
            native_identifier="camera-white-balance-custom-gains",
        )

        controls = backend.list_controls(descriptor)
        controls_by_id = {control.control_id: control for control in controls}
        self.assertIn("white_balance_automatic", controls_by_id)
        self.assertIn("white_balance_temperature", controls_by_id)
        self.assertEqual(
            "boolean", controls_by_id["white_balance_automatic"].kind
        )
        self.assertEqual(
            "numeric", controls_by_id["white_balance_temperature"].kind
        )

        device = FakeCaptureDeviceClass._device
        backend.set_control_value(descriptor, "white_balance_automatic", False)
        backend.set_control_value(
            descriptor,
            "white_balance_temperature",
            5000,
        )
        self.assertEqual(
            [
                ("setWhiteBalanceMode", 0),
                ("setWhiteBalanceTemperature", 5000.0),
            ],
            device.calls,
        )

    def test_recording_container_helpers_track_supported_formats(self) -> None:
        """Assert recording helpers expose only supported video formats."""

        class FakeFormat:
            """Provide one simple Qt media file-format token."""

            def __init__(self, name: str) -> None:
                """Store the enum-style file-format name."""

                self.name = name

        class FakeQMediaFormat:
            """Provide the minimal media-format surface used by helpers."""

            class ConversionMode:
                """Expose the encode mode used by the helpers."""

                Encode = object()

            class FileFormat:
                """Expose the format tokens queried by the helpers."""

                AVI = FakeFormat("AVI")
                MPEG4 = FakeFormat("MPEG4")
                QuickTime = FakeFormat("QuickTime")

            def supportedFileFormats(
                self, mode: object
            ) -> tuple[FakeFormat, ...]:
                """Return the supported video formats for this runtime."""

                return (
                    self.FileFormat.QuickTime,
                    self.FileFormat.MPEG4,
                )

            def fileFormatDescription(self, file_format: FakeFormat) -> str:
                """Return one readable file-format label."""

                descriptions = {
                    "MPEG4": "MPEG-4 Video",
                    "QuickTime": "QuickTime Movie",
                }
                return descriptions[file_format.name]

            def fileFormatName(self, file_format: FakeFormat) -> str:
                """Return the enum-style file-format name."""

                return file_format.name

        fake_qt_multimedia = mock.MagicMock(QMediaFormat=FakeQMediaFormat)

        self.assertEqual(
            "MPEG-4 Video (*.mp4);;QuickTime Movie (*.mov)",
            build_recording_file_filter(fake_qt_multimedia),
        )
        self.assertEqual(
            ".mp4",
            _preferred_recording_output_suffix(fake_qt_multimedia),
        )

        output_path, file_format = _qt_recording_output_path_for_path(
            Path("/tmp/microscope"),
            fake_qt_multimedia,
        )
        self.assertEqual(Path("/tmp/microscope.mp4"), output_path)
        self.assertIs(file_format, FakeQMediaFormat.FileFormat.MPEG4)

        with self.assertRaises(CameraOutputError):
            _qt_recording_output_path_for_path(
                Path("/tmp/microscope.avi"),
                fake_qt_multimedia,
            )

    @mock.patch(
        "webcam_micro.camera.wrap_completion_handler",
        new=_identity_completion_handler,
    )
    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_camera_permission_helper_requests_macos_prompt(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert the macOS helper requests camera access explicitly."""

        class FakeLoop:
            """Provide the minimal Qt event-loop surface for the helper."""

            def __init__(self) -> None:
                """Initialize the test event-loop bookkeeping."""

                self.quit_called = False
                self.exec_called = False

            def quit(self) -> None:
                """Record that the helper asked the loop to stop."""

                self.quit_called = True

            def exec(self) -> None:
                """Record that the helper entered the loop."""

                self.exec_called = True

        class FakeQtCore:
            """Provide the QtCore pieces used by the permission helper."""

            QEventLoop = FakeLoop

        class FakeCaptureDeviceClass:
            """Record the macOS permission request path."""

            requested_media_types: list[object] = []

            @staticmethod
            def authorizationStatusForMediaType_(media_type: object) -> int:
                """Return the prompt-needed authorization state."""

                return 0

            @classmethod
            def requestAccessForMediaType_completionHandler_(
                cls,
                media_type: object,
                completion_handler,
            ) -> None:
                """Record the prompt request and invoke the callback."""

                cls.requested_media_types.append(media_type)
                completion_handler(True)

        media_type = object()
        load_modules.return_value = (FakeCaptureDeviceClass, media_type)

        granted, notice = request_camera_permission(FakeQtCore)

        self.assertTrue(granted)
        self.assertEqual("", notice)
        self.assertEqual(
            [media_type], FakeCaptureDeviceClass.requested_media_types
        )

    def test_camera_permission_helper_mentions_callback_names(self) -> None:
        """Assert the permission helper keeps the callback symbols visible."""

        macos_source = inspect.getsource(_request_macos_camera_permission)
        qt_source = inspect.getsource(_request_qt_camera_permission)

        self.assertIn("completion_handler", macos_source)
        self.assertIn("PermissionReceiver", qt_source)
        self.assertIn("on_permission", qt_source)

    def test_null_backend_discovers_no_cameras(self) -> None:
        """Assert the fallback backend stays empty by design."""

        backend = NullCameraBackend()
        control_backend = NullCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="null-camera",
            display_name="Null Camera",
            backend_name=backend.backend_name,
            device_selector="null-camera",
        )

        self.assertEqual((), backend.discover_cameras())
        self.assertEqual(
            (),
            backend.list_controls(descriptor),
        )
        self.assertEqual((), control_backend.list_controls(descriptor))

    def test_null_backend_opens_placeholder_session(self) -> None:
        """Assert the fallback backend still provides session semantics."""

        backend = NullCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="stage1-demo",
            display_name="Stage 1 Demo Camera",
            backend_name=backend.backend_name,
            device_selector="stage1-demo",
        )

        session = backend.open_session(descriptor)

        self.assertFalse(session.closed)
        self.assertIsInstance(session, NullCameraSession)
        self.assertEqual(descriptor, session.descriptor)
        self.assertIsNone(session.failure_reason)
        self.assertIsNone(session.get_latest_frame())
        self.assertFalse(session.recording_available)
        self.assertEqual("not ready", session.recording_state)
        self.assertEqual(0, session.recording_duration_milliseconds)
        self.assertIsNone(session.recording_output_path)
        self.assertIsNone(session.recording_error)
        with self.assertRaises(CameraOutputError):
            session.start_recording(
                Path("/tmp/null-camera.mp4"),
                crop_plan=RecordingCropPlan(
                    source_x=0,
                    source_y=0,
                    source_width=320,
                    source_height=240,
                ),
            )
        self.assertIsNone(session.stop_recording())
        session.close()
        self.assertTrue(session.closed)

    def test_null_backend_rejects_control_writes(self) -> None:
        """Assert the fallback backend fails softly on control writes."""

        backend = NullCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="null-camera",
            display_name="Null Camera",
            backend_name=backend.backend_name,
            device_selector="null-camera",
        )

        with self.assertRaises(CameraControlApplyError):
            backend.set_control_value(descriptor, "zoom_factor", 2.0)
        with self.assertRaises(CameraControlApplyError):
            backend.trigger_control_action(
                descriptor,
                "restore_auto_exposure",
            )

        control_backend = NullCameraControlBackend()
        with self.assertRaises(CameraControlApplyError):
            control_backend.trigger_control_action(
                descriptor,
                "restore_auto_exposure",
            )

    def test_camera_control_preserves_typed_metadata(self) -> None:
        """Assert control dataclasses preserve the metadata contract."""

        control = CameraControl(
            control_id="zoom_factor",
            label="Zoom Factor",
            kind="numeric",
            value=1.0,
            choices=(CameraControlChoice(value="one", label="One"),),
            min_value=1.0,
            max_value=4.0,
            step=0.1,
            read_only=False,
            enabled=True,
            unit="x",
            details="Camera zoom factor.",
            action_label="Reset",
        )

        self.assertEqual("zoom_factor", control.control_id)
        self.assertEqual("Zoom Factor", control.label)
        self.assertEqual("numeric", control.kind)
        self.assertEqual(1.0, control.value)
        self.assertEqual("one", control.choices[0].value)
        self.assertEqual("One", control.choices[0].label)
        self.assertEqual(1.0, control.min_value)
        self.assertEqual(4.0, control.max_value)
        self.assertEqual(0.1, control.step)
        self.assertFalse(control.read_only)
        self.assertTrue(control.enabled)
        self.assertEqual("x", control.unit)
        self.assertEqual("Camera zoom factor.", control.details)
        self.assertEqual("Reset", control.action_label)

    def test_preview_frame_preserves_rgb_dimensions(self) -> None:
        """Assert preview frames carry the UI-ready RGB payload metadata."""

        frame = PreviewFrame(
            width=320,
            height=240,
            rgb_bytes=b"rgb",
            frame_number=4,
        )

        self.assertEqual(320, frame.width)
        self.assertEqual(240, frame.height)
        self.assertEqual(b"rgb", frame.rgb_bytes)
        self.assertEqual(4, frame.frame_number)

    def test_pack_preview_rgb_rows_removes_row_padding(self) -> None:
        """Assert padded RGB rows compact into one packed preview payload."""

        self.assertEqual(
            bytes(range(12)),
            pack_preview_rgb_rows(
                bytes(
                    [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        90,
                        91,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        92,
                        93,
                    ]
                ),
                width=2,
                height=2,
                bytes_per_line=8,
            ),
        )
